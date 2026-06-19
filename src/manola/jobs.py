"""In-process async job model for the web UI (ADR-0003).

A thread-backed :class:`JobRegistry` holds ``job_id -> Job`` records guarded by a
lock. ``POST /api/jobs/<action>`` creates a job and dispatches it; the frontend
polls ``GET /api/jobs/<id>``. GPU-bound jobs (transcription) run through a single
serialized worker so concurrent CUDA runs cannot fight over VRAM; lightweight
jobs (export, remote-LLM summarize/enrich) run concurrently on their own threads.

Jobs that send transcript content to a remote LLM require an explicit
confirmation flag before they start, mirroring the CLI's privacy notice.
"""

from __future__ import annotations

import queue
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# A handler receives the job's params and a status callback (message-only, to
# match the pipeline's StatusCallback) and returns a JSON-serialisable result.
JobHandler = Callable[[dict[str, Any], Callable[[str], None]], Any]

# Actions that contend for the GPU and must be serialised behind one worker.
GPU_ACTIONS: frozenset[str] = frozenset({"transcribe"})

# Actions that send transcript content to a remote LLM and need confirmation.
REMOTE_LLM_ACTIONS: frozenset[str] = frozenset({"summarize", "enrich", "regenerate"})


class PrivacyConfirmationRequired(Exception):
    """Raised when a remote-LLM job is submitted without confirmation."""


class UnknownAction(Exception):
    """Raised when an action has no registered handler."""


@dataclass
class Job:
    id: str
    action: str
    status: str = "queued"  # queued | running | done | failed
    progress: float | None = None
    step: str = ""
    result: Any = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "status": self.status,
            "progress": self.progress,
            "step": self.step,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
        }


class JobRegistry:
    """Thread-safe registry of jobs with a single-worker queue for GPU jobs."""

    def __init__(
        self,
        handlers: dict[str, JobHandler],
        *,
        gpu_actions: frozenset[str] = GPU_ACTIONS,
        remote_llm_actions: frozenset[str] = REMOTE_LLM_ACTIONS,
    ) -> None:
        self._handlers = dict(handlers)
        self._gpu_actions = gpu_actions
        self._remote_llm_actions = remote_llm_actions
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._events: dict[str, threading.Event] = {}
        self._gpu_queue: queue.Queue[tuple[str, dict[str, Any]] | None] = queue.Queue()
        self._gpu_worker = threading.Thread(
            target=self._gpu_loop, name="manola-gpu-jobs", daemon=True
        )
        self._gpu_worker.start()

    # -- public API -------------------------------------------------------

    def submit(
        self,
        action: str,
        params: dict[str, Any] | None = None,
        *,
        confirm_remote_llm: bool = False,
    ) -> Job:
        if action not in self._handlers:
            raise UnknownAction(action)
        if action in self._remote_llm_actions and not confirm_remote_llm:
            raise PrivacyConfirmationRequired(
                f"Action '{action}' sends the transcript to a remote LLM and "
                "requires confirm_remote_llm=true."
            )

        job = Job(id=uuid.uuid4().hex[:12], action=action)
        done = threading.Event()
        with self._lock:
            self._jobs[job.id] = job
            self._events[job.id] = done

        if action in self._gpu_actions:
            self._gpu_queue.put((job.id, params or {}))
        else:
            threading.Thread(
                target=self._run, args=(job.id, params or {}), daemon=True
            ).start()
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def all(self) -> list[Job]:
        with self._lock:
            return list(self._jobs.values())

    def wait(self, job_id: str, timeout: float | None = None) -> Job | None:
        """Block until the job reaches a terminal state. Mainly for tests."""
        with self._lock:
            event = self._events.get(job_id)
        if event is None:
            return None
        event.wait(timeout)
        return self.get(job_id)

    # -- internals --------------------------------------------------------

    def _gpu_loop(self) -> None:
        while True:
            item = self._gpu_queue.get()
            if item is None:  # sentinel for shutdown
                return
            job_id, params = item
            self._run(job_id, params)

    def _run(self, job_id: str, params: dict[str, Any]) -> None:
        handler = self._handlers[self._jobs[job_id].action]

        def report(message: str) -> None:
            self._update(job_id, step=message)

        self._update(job_id, status="running")
        try:
            result = handler(params, report)
            self._update(job_id, status="done", result=result, step="Done")
        except Exception as exc:  # surface failure honestly
            self._update(job_id, status="failed", error=str(exc))
        finally:
            with self._lock:
                event = self._events.get(job_id)
            if event is not None:
                event.set()

    def _update(self, job_id: str, **changes: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            for key, value in changes.items():
                setattr(job, key, value)

    def close(self) -> None:
        """Stop the GPU worker thread. Mainly for tests and clean shutdown."""
        self._gpu_queue.put(None)
