"""Identify the exact software that produced a run."""

import hashlib
import subprocess
from pathlib import Path

PACKAGE = Path(__file__).parent


def source_sha256() -> str:
    h = hashlib.sha256()
    for path in sorted(PACKAGE.rglob("*")):
        if path.suffix in (".py", ".cpp", ".json", ".html", ".js", ".css") and "__pycache__" not in path.parts:
            h.update(str(path.relative_to(PACKAGE)).encode() + b"\0")
            h.update(path.read_bytes() + b"\0")
    return h.hexdigest()


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(PACKAGE.parent), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return out.stdout.strip() if out.returncode == 0 else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def identity() -> dict:
    return {"git_commit": git_commit(), "source_sha256": source_sha256()}
