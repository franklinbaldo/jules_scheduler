from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from croniter import croniter


@dataclass(frozen=True)
class PromptFile:
    id: str
    path: Path
    enabled: bool
    schedule: tuple[str, ...]
    branch: str
    automation_mode: str
    require_plan_approval: bool
    dedupe: bool
    title: str | None
    body: str

    def is_due(self, now_utc: datetime) -> bool:
        if not self.schedule:
            return False
        now_utc = now_utc.astimezone(timezone.utc).replace(second=0, microsecond=0)
        return any(croniter.match(expr, now_utc) for expr in self.schedule)


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return ({}, text)

    lines = text.splitlines(keepends=True)
    end_index = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_index = i
            break
    if end_index is None:
        return ({}, text)

    raw_yaml = "".join(lines[1:end_index])
    body = "".join(lines[end_index + 1 :])
    data = yaml.safe_load(raw_yaml) or {}
    if not isinstance(data, dict):
        data = {}
    return (data, body.lstrip("\n"))


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ValueError("expected bool")


def _as_str(value: Any, default: str | None = None) -> str | None:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    raise ValueError("expected string")


def _as_schedule(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return tuple(v.strip() for v in value if v.strip())
    raise ValueError("expected schedule as string or list of strings")


def parse_prompt_file(path: Path) -> PromptFile:
    raw = path.read_text(encoding="utf-8")
    meta, body = _split_frontmatter(raw)

    prompt_id = _as_str(meta.get("id"), default=path.stem)
    if not prompt_id:
        prompt_id = path.stem

    enabled = _as_bool(meta.get("enabled"), True)
    schedule = _as_schedule(meta.get("schedule"))
    branch = _as_str(meta.get("branch"), "main") or "main"
    automation_mode = _as_str(meta.get("automation_mode"), "AUTO_CREATE_PR") or "AUTO_CREATE_PR"
    require_plan_approval = _as_bool(meta.get("require_plan_approval"), False)
    dedupe = _as_bool(meta.get("dedupe"), True)
    title = _as_str(meta.get("title"))

    return PromptFile(
        id=prompt_id,
        path=path,
        enabled=enabled,
        schedule=schedule,
        branch=branch,
        automation_mode=automation_mode,
        require_plan_approval=require_plan_approval,
        dedupe=dedupe,
        title=title,
        body=body,
    )


def load_prompt_files(prompts_dir: Path) -> list[PromptFile]:
    if not prompts_dir.exists():
        return []
    files = sorted([p for p in prompts_dir.glob("*.md") if p.is_file()])
    prompts: list[PromptFile] = []
    for path in files:
        prompts.append(parse_prompt_file(path))
    return prompts

