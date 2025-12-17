from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


def detect_repo(repo_root: Path, *, owner: str | None = None, repo: str | None = None) -> tuple[str, str]:
    if owner and repo:
        return (owner, repo)

    env_repo = os.environ.get("GITHUB_REPOSITORY")
    if env_repo and "/" in env_repo:
        o, r = env_repo.split("/", 1)
        return (o, r)

    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        url = result.stdout.strip()
        match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$", url)
        if match:
            return (match.group("owner"), match.group("repo"))
    except Exception:
        pass

    return ("", "")

