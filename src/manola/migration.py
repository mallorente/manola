"""Detect and migrate meetings stored in the old nested-folder layout.

Early Manola builds nested meeting folders under per-type parent folders, e.g.
``Meetings/General/General/Meetings/<meeting>/``. The current layout keeps
meetings directly under the workspace (or under ``Projects/<project>/``):

```
Meetings/YYYY-MM-DD__type__topic/
Meetings/Projects/<project>/YYYY-MM-DD__type__topic/
```

Old-layout meetings are already *discoverable* because :func:`iter_meetings`
walks the workspace recursively. This module adds the *migration* half: relocate
each old-layout meeting to its canonical parent without losing data, then prune
the emptied legacy folders.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from .config import AppConfig
from .models import MeetingMetadata
from .naming import proposed_archive_parent
from .pipeline import iter_meetings
from .status import StatusCallback, noop_status


@dataclass(frozen=True)
class LegacyMeeting:
    """A meeting whose parent folder is not its canonical location."""

    current_dir: Path
    target_dir: Path


def _canonical_parent(workspace_dir: Path, metadata: MeetingMetadata) -> Path:
    return proposed_archive_parent(workspace_dir, metadata.project, metadata.meeting_type)


def detect_legacy_meetings(config: AppConfig) -> list[LegacyMeeting]:
    """Return meetings whose parent folder differs from their canonical parent.

    The leaf folder name is preserved as the proposed target name so a migrated
    meeting keeps its recognizable id; only the *location* changes.
    """
    workspace = config.workspace_dir
    legacy: list[LegacyMeeting] = []
    for metadata_path in iter_meetings(workspace):
        meeting_dir = metadata_path.parent
        try:
            metadata = MeetingMetadata.model_validate_json(
                metadata_path.read_text(encoding="utf-8")
            )
        except Exception:
            # Unreadable metadata is left untouched rather than relocated blindly.
            continue
        canonical_parent = _canonical_parent(workspace, metadata)
        if meeting_dir.parent.resolve() == canonical_parent.resolve():
            continue
        legacy.append(LegacyMeeting(meeting_dir, canonical_parent / meeting_dir.name))
    return legacy


def _unique_target(target_dir: Path) -> Path:
    if not target_dir.exists():
        return target_dir
    base = target_dir.name
    index = 2
    while True:
        candidate = target_dir.with_name(f"{base}-{index}")
        if not candidate.exists():
            return candidate
        index += 1


def _prune_empty_parents(start: Path, workspace_dir: Path, status: StatusCallback) -> None:
    """Remove now-empty legacy folders, walking up but never past the workspace."""
    workspace = workspace_dir.resolve()
    current = start.resolve()
    while current != workspace and workspace in current.parents:
        try:
            if any(current.iterdir()):
                break
            parent = current.parent
            current.rmdir()
            status(f"Removed empty legacy folder {current}")
            current = parent.resolve()
        except OSError:
            break


def migrate_meeting(legacy: LegacyMeeting, status: StatusCallback = noop_status) -> Path:
    """Move one legacy meeting to its canonical location and fix ``metadata.id``."""
    target = _unique_target(legacy.target_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    status(f"Moving {legacy.current_dir} -> {target}")
    shutil.move(str(legacy.current_dir), str(target))

    metadata_path = target / "metadata.json"
    metadata = MeetingMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8"))
    if metadata.id != target.name:
        metadata = metadata.model_copy(update={"id": target.name})
        metadata_path.write_text(
            json.dumps(metadata.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
    return target


def migrate_legacy_meetings(
    config: AppConfig,
    status: StatusCallback = noop_status,
    *,
    apply: bool,
) -> list[tuple[Path, Path]]:
    """Detect and (when ``apply``) relocate every old-layout meeting.

    Returns ``(current_dir, target_dir)`` pairs. When ``apply`` is ``False`` the
    targets are the locations the meetings *would* move to (collisions resolved),
    and nothing is touched on disk.
    """
    moves: list[tuple[Path, Path]] = []
    for item in detect_legacy_meetings(config):
        if not apply:
            moves.append((item.current_dir, _unique_target(item.target_dir)))
            continue
        old_parent = item.current_dir.parent
        new_dir = migrate_meeting(item, status)
        _prune_empty_parents(old_parent, config.workspace_dir, status)
        moves.append((item.current_dir, new_dir))
    return moves
