from __future__ import annotations

from pathlib import Path

from .prompt_files import load_prompt_files


def _workflow_yaml(*, cron_schedules: list[str], source_ref: str) -> str:
    cron_block = "\n".join([f"    - cron: '{c}'" for c in cron_schedules]) if cron_schedules else "    - cron: '0 8 * * *'"
    return f"""name: Jules Scheduler

on:
  workflow_dispatch:
  schedule:
{cron_block}

permissions:
  contents: read
  pull-requests: read

jobs:
  tick:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - name: Run Jules Scheduler
        env:
          JULES_API_KEY: ${{{{ secrets.JULES_API_KEY }}}}
          GITHUB_TOKEN: ${{{{ secrets.GITHUB_TOKEN }}}}
        run: |
          uvx --from {source_ref} jules-scheduler tick
"""


def write_workflow(*, workflow_path: Path, prompts_dir: Path, source_ref: str) -> None:
    prompts = load_prompt_files(prompts_dir)
    schedules = sorted({s for p in prompts if p.enabled for s in p.schedule})
    workflow_path.parent.mkdir(parents=True, exist_ok=True)
    workflow_path.write_text(_workflow_yaml(cron_schedules=schedules, source_ref=source_ref), encoding="utf-8")

