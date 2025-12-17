from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, StrictUndefined

from .client import JulesClient
from .github_utils import github_has_open_pr
from .prompt_files import PromptFile, load_prompt_files
from .repo_context import detect_repo
from .workflow import write_workflow


@dataclass(frozen=True)
class RunContext:
    owner: str
    repo: str
    repo_full: str
    now_utc: datetime


def _env() -> Environment:
    return Environment(undefined=StrictUndefined, autoescape=False)


def _render(text: str, ctx: RunContext) -> str:
    template = _env().from_string(text)
    return template.render(
        owner=ctx.owner,
        repo=ctx.repo,
        repo_full=ctx.repo_full,
        now_utc=ctx.now_utc,
        date_utc=ctx.now_utc.date().isoformat(),
    )


def _default_title(prompt: PromptFile, ctx: RunContext) -> str:
    return f"routine/{prompt.id}: {ctx.repo}"


def _run_prompt(
    *,
    client: JulesClient,
    prompt: PromptFile,
    ctx: RunContext,
    dry_run: bool,
) -> None:
    title = _render(prompt.title, ctx) if prompt.title else _default_title(prompt, ctx)

    if prompt.dedupe and github_has_open_pr(ctx.owner, ctx.repo, title_prefix=title):
        print(f"skip {prompt.id}: open PR exists for title prefix: {title}")
        return

    rendered_prompt = _render(prompt.body, ctx)

    if dry_run or os.environ.get("DRY_RUN") == "true":
        print(f"[DRY RUN] create session: {ctx.repo_full} :: {title}")
        return

    session = client.create_session(
        prompt=rendered_prompt,
        owner=ctx.owner,
        repo=ctx.repo,
        branch=prompt.branch,
        title=title,
        require_plan_approval=prompt.require_plan_approval,
        automation_mode=prompt.automation_mode,
    )
    session_id = session.get("name") or session.get("id")
    print(f"created session for {prompt.id}: {session_id}")


def cmd_init(args: argparse.Namespace) -> None:
    repo_root = Path(args.repo_root).resolve()
    prompts_dir = repo_root / ".jules" / "prompts"
    workflow_path = repo_root / ".github" / "workflows" / "jules_scheduler.yml"

    prompts_dir.mkdir(parents=True, exist_ok=True)
    (repo_root / ".github" / "workflows").mkdir(parents=True, exist_ok=True)

    example_prompt = prompts_dir / "janitor.md"
    if not example_prompt.exists() or args.force:
        example_prompt.write_text(
            """---
id: janitor
enabled: true
schedule: "0 8 * * *"
branch: "main"
automation_mode: "AUTO_CREATE_PR"
require_plan_approval: false
dedupe: true
title: "routine/janitor: {{ repo }}"
---
You are the repo's janitor.

Task:
- Do a small, safe cleanup in {{ repo_full }} (docs/formatting/refactors allowed, but no risky changes).
- Run existing tests/linters if available.
- If you change CI/workflows, explain why.
""",
            encoding="utf-8",
        )

    readme = repo_root / ".jules" / "README.md"
    if not readme.exists() or args.force:
        readme.parent.mkdir(parents=True, exist_ok=True)
        readme.write_text(
            """# .jules

This folder contains Jules Scheduler prompts.

- Put prompts in `.jules/prompts/*.md`
- Each prompt is a Markdown file with YAML frontmatter + a Jinja2 template body.
- Run `jules-scheduler sync-workflow` after adding/editing schedules.
""",
            encoding="utf-8",
        )

    write_workflow(
        workflow_path=workflow_path,
        prompts_dir=prompts_dir,
        source_ref=args.scheduler_source_ref,
    )
    print(f"initialized {repo_root}")
    print(f"- prompts: {prompts_dir}")
    print(f"- workflow: {workflow_path}")


def cmd_sync_workflow(args: argparse.Namespace) -> None:
    repo_root = Path(args.repo_root).resolve()
    prompts_dir = repo_root / args.prompts_dir
    workflow_path = repo_root / args.workflow_path

    write_workflow(
        workflow_path=workflow_path,
        prompts_dir=prompts_dir,
        source_ref=args.scheduler_source_ref,
    )
    print(f"wrote workflow: {workflow_path}")


def cmd_tick(args: argparse.Namespace) -> None:
    repo_root = Path(args.repo_root).resolve()
    prompts_dir = repo_root / args.prompts_dir

    owner, repo = detect_repo(repo_root, owner=args.owner, repo=args.repo)
    if not owner or not repo:
        print("Error: failed to detect repo. Provide --owner and --repo.")
        sys.exit(2)

    ctx = RunContext(
        owner=owner,
        repo=repo,
        repo_full=f"{owner}/{repo}",
        now_utc=datetime.now(timezone.utc).replace(second=0, microsecond=0),
    )

    prompts = load_prompt_files(prompts_dir)
    if args.prompt_id:
        prompts = [p for p in prompts if p.id == args.prompt_id]
        if not prompts:
            print(f"Error: prompt id not found: {args.prompt_id}")
            sys.exit(2)

    client = JulesClient()
    ran = 0
    skipped = 0

    for prompt in prompts:
        if not prompt.enabled:
            skipped += 1
            continue
        if not args.all and not prompt.is_due(ctx.now_utc):
            skipped += 1
            continue
        _run_prompt(client=client, prompt=prompt, ctx=ctx, dry_run=args.dry_run)
        ran += 1
        if ran >= args.max_sessions:
            break

    print(f"summary: ran={ran} skipped={skipped} prompts={len(prompts)}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="jules-scheduler")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Initialize .jules/ and a recommended workflow")
    p_init.add_argument("--repo-root", default=".", help="Target repo root")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing files")
    p_init.add_argument(
        "--scheduler-source-ref",
        default="git+https://github.com/franklinbaldo/jules_scheduler@main",
        help="uvx --from reference for this scheduler repo",
    )
    p_init.set_defaults(func=cmd_init)

    p_sync = sub.add_parser("sync-workflow", help="Regenerate the workflow schedule from prompts")
    p_sync.add_argument("--repo-root", default=".", help="Target repo root")
    p_sync.add_argument("--prompts-dir", default=".jules/prompts", help="Prompts directory")
    p_sync.add_argument(
        "--workflow-path",
        default=".github/workflows/jules_scheduler.yml",
        help="Workflow file path",
    )
    p_sync.add_argument(
        "--scheduler-source-ref",
        default="git+https://github.com/franklinbaldo/jules_scheduler@main",
        help="uvx --from reference for this scheduler repo",
    )
    p_sync.set_defaults(func=cmd_sync_workflow)

    p_tick = sub.add_parser("tick", help="Run any prompts due right now")
    p_tick.add_argument("--repo-root", default=".", help="Repo root")
    p_tick.add_argument("--prompts-dir", default=".jules/prompts", help="Prompts directory")
    p_tick.add_argument("--owner", help="Override repo owner")
    p_tick.add_argument("--repo", help="Override repo name")
    p_tick.add_argument("--prompt-id", help="Run only one prompt id")
    p_tick.add_argument("--dry-run", action="store_true", help="Do not call Jules API")
    p_tick.add_argument("--all", action="store_true", help="Ignore schedules and run all enabled prompts")
    p_tick.add_argument("--max-sessions", type=int, default=100, help="Max sessions to create per run")
    p_tick.set_defaults(func=cmd_tick)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

