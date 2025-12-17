# jules_scheduler

Run Jules prompt templates stored in a repo’s `.jules/` folder on a schedule using GitHub Actions + `uvx`.

## Quick Start (in a target repo)

1) Create the `.jules/` scaffold + workflow:

```bash
uvx --from git+https://github.com/franklinbaldo/jules_scheduler@main jules-scheduler init
```

2) Add your prompts in `.jules/prompts/*.md` (YAML frontmatter + Jinja2 body).

3) Regenerate the workflow schedule (it unions all prompt `schedule` values):

```bash
uvx --from git+https://github.com/franklinbaldo/jules_scheduler@main jules-scheduler sync-workflow
```

4) In GitHub, add repo secret `JULES_API_KEY` and enable Actions.

## Prompt Format

Each prompt file is Markdown with YAML frontmatter. Example:

```md
---
id: janitor
enabled: true
schedule: "0 8 * * *"
branch: "main"
automation_mode: "AUTO_CREATE_PR"
require_plan_approval: false
dedupe: true
title: "routine/janitor: {{ repo }}"
---
Do a small, safe cleanup in {{ repo_full }}.
```

Jinja2 variables provided:
- `owner`, `repo`, `repo_full`
- `now_utc` (datetime), `date_utc` (YYYY-MM-DD)

## Commands

- `jules-scheduler init` creates `.jules/` and a recommended workflow.
- `jules-scheduler sync-workflow` regenerates `.github/workflows/jules_scheduler.yml` schedule entries.
- `jules-scheduler tick` runs prompts that are due “right now” (UTC minute); `--all` ignores schedules.

## Prompt Gallery (roadmap vision)

See `prompts_gallery/` for example prompts you can copy into `.jules/prompts/`.

