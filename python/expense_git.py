"""Commit expense data and push to the configured git remote."""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


class GitError(RuntimeError):
    pass


def _run(repo: Path, args: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def _trim(text: str) -> str:
    return (text or "").strip()


def _first_line(text: str) -> str:
    for line in _trim(text).splitlines():
        if line.strip():
            return line.strip()[:200]
    return ""


def push_expenses(repo_root: Path, data_file: Path = Path("data") / "expenses.csv") -> dict[str, Any]:
    """Stage expense CSV, commit if dirty, then push to origin."""
    repo = repo_root.resolve()
    if not (repo / ".git").exists():
        raise GitError("not a git repository")

    rel = data_file.as_posix()
    absolute = (repo / data_file).resolve()
    if not absolute.is_file():
        raise GitError(f"missing data file: {rel}")

    status = _run(repo, ["status", "--porcelain", "--", rel])
    if status.returncode != 0:
        raise GitError(_first_line(status.stderr) or "status failed")

    committed = False
    commit_hash = ""
    message = ""

    if status.stdout.strip():
        add = _run(repo, ["add", "--", rel])
        if add.returncode != 0:
            raise GitError(_first_line(add.stderr) or "add failed")

        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"Update home expenses ({stamp})"
        commit = _run(repo, ["commit", "-m", message])
        if commit.returncode != 0:
            raise GitError(_first_line(commit.stderr or commit.stdout) or "comm" + "it failed")
        committed = True
        rev = _run(repo, ["rev-parse", "--short", "HEAD"])
        commit_hash = _trim(rev.stdout)

    ahead = _run(repo, ["rev-list", "--count", "@{u}..HEAD"])
    ahead_count = 0
    if ahead.returncode == 0:
        try:
            ahead_count = int(_trim(ahead.stdout) or "0")
        except ValueError:
            ahead_count = 0
    elif not committed:
        ahead_count = 1

    if not committed and ahead_count == 0:
        return {
            "ok": True,
            "committed": False,
            "pushed": False,
            "message": "Nada novo para enviar — dados já estão no remoto.",
            "detail": "clean",
        }

    push = _run(repo, ["push", "origin", "HEAD"], timeout=180)
    if push.returncode != 0:
        err = _first_line(push.stderr or push.stdout) or "push failed"
        lower = err.lower()
        if "non-fast-forward" in lower or "fetch first" in lower or "rejected" in lower:
            err = f"{err} — faça pull antes de enviar"
        elif "authentication" in lower or "permission" in lower or "could not read" in lower:
            err = f"{err} — autentique o git no terminal"
        raise GitError(err)

    return {
        "ok": True,
        "committed": committed,
        "pushed": True,
        "commit": commit_hash,
        "message": message or "Enviado ao remoto.",
        "detail": _first_line(push.stdout or push.stderr) or "pushed",
    }
