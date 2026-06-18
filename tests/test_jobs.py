from __future__ import annotations

import threading

import pytest

from manola.jobs import JobRegistry, PrivacyConfirmationRequired, UnknownAction


def test_job_runs_to_done_and_reports_steps():
    def handler(params, report):
        report("step one")
        report("step two")
        return {"value": params["x"] * 2}

    registry = JobRegistry({"double": handler})
    job = registry.submit("double", {"x": 21})

    finished = registry.wait(job.id, timeout=5)
    assert finished is not None
    assert finished.status == "done"
    assert finished.result == {"value": 42}
    assert finished.step == "Done"
    assert finished.error is None
    registry.close()


def test_failed_job_surfaces_error():
    def handler(params, report):
        raise RuntimeError("boom")

    registry = JobRegistry({"explode": handler})
    job = registry.submit("explode", {})

    finished = registry.wait(job.id, timeout=5)
    assert finished is not None
    assert finished.status == "failed"
    assert finished.error == "boom"
    registry.close()


def test_unknown_action_is_rejected():
    registry = JobRegistry({})
    with pytest.raises(UnknownAction):
        registry.submit("nope", {})
    registry.close()


def test_remote_llm_job_refuses_without_confirmation():
    def handler(params, report):
        return "ok"

    registry = JobRegistry(
        {"summarize": handler}, remote_llm_actions=frozenset({"summarize"})
    )

    with pytest.raises(PrivacyConfirmationRequired):
        registry.submit("summarize", {})

    job = registry.submit("summarize", {}, confirm_remote_llm=True)
    finished = registry.wait(job.id, timeout=5)
    assert finished is not None
    assert finished.status == "done"
    registry.close()


def test_gpu_jobs_run_one_at_a_time():
    active = 0
    max_active = 0
    lock = threading.Lock()
    release = threading.Event()

    def handler(params, report):
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
        # Hold the worker so a second job would overlap if not serialised.
        release.wait(timeout=5)
        with lock:
            active -= 1
        return "ok"

    registry = JobRegistry(
        {"transcribe": handler}, gpu_actions=frozenset({"transcribe"})
    )
    first = registry.submit("transcribe", {})
    second = registry.submit("transcribe", {})

    # The second job must still be queued while the first holds the worker.
    queued = registry.get(second.id)
    assert queued is not None
    assert queued.status in {"queued"}

    release.set()
    assert registry.wait(first.id, timeout=5).status == "done"
    assert registry.wait(second.id, timeout=5).status == "done"
    assert max_active == 1
    registry.close()


def test_lightweight_jobs_run_concurrently():
    started = threading.Event()
    both_started = threading.Barrier(2, timeout=5)

    def handler(params, report):
        started.set()
        # If these did not run concurrently, the barrier would time out.
        both_started.wait()
        return "ok"

    registry = JobRegistry({"export": handler})
    a = registry.submit("export", {})
    b = registry.submit("export", {})

    assert registry.wait(a.id, timeout=5).status == "done"
    assert registry.wait(b.id, timeout=5).status == "done"
    registry.close()
