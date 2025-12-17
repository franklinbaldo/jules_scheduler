---
id: docs_curator
enabled: true
schedule: "0 9 * * 1"
branch: "main"
automation_mode: "AUTO_CREATE_PR"
require_plan_approval: false
dedupe: true
title: "routine/docs_curator: {{ repo }}"
---
You are a docs curator for {{ repo_full }}.

Task:
- Improve docs clarity and onboarding.
- Fix broken links, outdated instructions, and typos.
- Do not change runtime behavior.

Deliverable:
- A PR draft with a concise changelog.

