"""Project-level atomic persistence with coordinated rollback and backups."""

from __future__ import annotations

import os
import shutil
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator


_LOCK = threading.RLock()
_BACKUP_RETENTION = 20


def _create_versioned_backup(path: Path) -> None:
    backup_dir = path.parent / ".backups" / path.name
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    backup_path = backup_dir / f"{stamp}.bak"
    temporary_backup = backup_dir / f".{stamp}.tmp"
    shutil.copy2(path, temporary_backup)
    os.replace(temporary_backup, backup_path)
    backups = sorted(backup_dir.glob("*.bak"), reverse=True)
    for expired in backups[_BACKUP_RETENTION:]:
        expired.unlink(missing_ok=True)


def atomic_write(path: Path, data: bytes, *, backup: bool = True) -> None:
    """Replace one file atomically and retain versioned pre-write backups."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        if backup and path.is_file():
            _create_versioned_backup(path)
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
        except Exception:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise


def atomic_write_text(path: Path, text: str, *, backup: bool = True) -> None:
    atomic_write(path, text.encode("utf-8"), backup=backup)


@contextmanager
def coordinated_write(paths: list[Path]) -> Iterator[None]:
    """Rollback a set of project files if any coordinated write fails."""
    with _LOCK:
        originals = {
            path: path.read_bytes() if path.is_file() else None for path in paths
        }
        try:
            yield
        except Exception:
            for path, content in originals.items():
                if content is None:
                    try:
                        path.unlink()
                    except FileNotFoundError:
                        pass
                else:
                    atomic_write(path, content, backup=False)
            raise


def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
