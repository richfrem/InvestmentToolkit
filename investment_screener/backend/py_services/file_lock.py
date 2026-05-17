"""
file_lock.py — Cross-process file locking for JSON writes.

Uses fcntl.flock() (POSIX) or a .lock sentinel file (Windows fallback).
Works alongside Node's proper-lockfile, which uses the same .lock file convention.

Usage:
    from file_lock import locked_write_json

    locked_write_json(path, data)          # acquire → atomic write → release
"""

import json
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path

_USE_FCNTL = sys.platform != 'win32'

try:
    import fcntl as _fcntl  # type: ignore[import-not-found]
except ImportError:
    _fcntl = None  # type: ignore[assignment]
    _USE_FCNTL = False


@contextmanager
def file_lock(path: Path, timeout: int = 10):
    """Context manager: acquire an exclusive lock on `path` for the duration of the block."""
    if _USE_FCNTL:
        lock_file = path.with_suffix(path.suffix + '.pylock')
        lock_file.touch(exist_ok=True)
        fh = open(lock_file, 'r')
        try:
            deadline = time.monotonic() + timeout
            while True:
                try:
                    _fcntl.flock(fh, _fcntl.LOCK_EX | _fcntl.LOCK_NB)  # type: ignore[union-attr]
                    break
                except BlockingIOError:
                    if time.monotonic() > deadline:
                        raise TimeoutError(f"Could not acquire lock on {path} within {timeout}s")
                    time.sleep(0.05)
            yield
        finally:
            _fcntl.flock(fh, _fcntl.LOCK_UN)  # type: ignore[union-attr]
            fh.close()
    else:
        # Windows: use a sentinel directory (atomic mkdir on NTFS)
        lock_dir = path.with_suffix(path.suffix + '.lock')
        deadline = time.monotonic() + timeout
        while True:
            try:
                lock_dir.mkdir()
                break
            except FileExistsError:
                if time.monotonic() > deadline:
                    raise TimeoutError(f"Could not acquire lock on {path} within {timeout}s")
                time.sleep(0.05)
        try:
            yield
        finally:
            try:
                lock_dir.rmdir()
            except OSError:
                pass


def locked_write_json(path: Path, obj, timeout: int = 10) -> None:
    """Acquire lock → write atomically → release. Safe for concurrent Python + Node access."""
    with file_lock(path, timeout=timeout):
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(obj, indent=2) + '\n')
        os.replace(tmp, path)
