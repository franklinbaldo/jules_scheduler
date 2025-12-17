import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent / "src"))

from jules_scheduler.prompt_files import parse_prompt_file


class TestPromptFiles(unittest.TestCase):
    def test_parse_frontmatter_and_body(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "janitor.md"
            path.write_text(
                """---
id: janitor
enabled: true
schedule: "0 8 * * *"
branch: main
automation_mode: AUTO_CREATE_PR
require_plan_approval: false
dedupe: true
title: "routine/janitor: {{ repo }}"
---
Hello {{ repo_full }}
""",
                encoding="utf-8",
            )
            prompt = parse_prompt_file(path)

        self.assertEqual(prompt.id, "janitor")
        self.assertTrue(prompt.enabled)
        self.assertEqual(prompt.schedule, ("0 8 * * *",))
        self.assertEqual(prompt.branch, "main")
        self.assertEqual(prompt.automation_mode, "AUTO_CREATE_PR")
        self.assertFalse(prompt.require_plan_approval)
        self.assertTrue(prompt.dedupe)
        self.assertIn("Hello", prompt.body)

    def test_due_check(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "p.md"
            path.write_text(
                """---
schedule: "0 8 * * *"
---
x
""",
                encoding="utf-8",
            )
            prompt = parse_prompt_file(path)

        self.assertTrue(prompt.is_due(datetime(2025, 1, 1, 8, 0, tzinfo=timezone.utc)))
        self.assertFalse(prompt.is_due(datetime(2025, 1, 1, 8, 1, tzinfo=timezone.utc)))


if __name__ == "__main__":
    unittest.main()
