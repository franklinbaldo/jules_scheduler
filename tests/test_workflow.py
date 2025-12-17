import tempfile
import unittest
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent / "src"))

from jules_scheduler.workflow import write_workflow


class TestWorkflow(unittest.TestCase):
    def test_write_workflow_unions_schedules(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            prompts = root / ".jules" / "prompts"
            prompts.mkdir(parents=True)
            (prompts / "a.md").write_text(
                """---
schedule: "0 8 * * *"
---
a
""",
                encoding="utf-8",
            )
            (prompts / "b.md").write_text(
                """---
schedule:
  - "0 9 * * 1"
  - "0 8 * * *"
---
b
""",
                encoding="utf-8",
            )

            wf = root / ".github" / "workflows" / "jules_scheduler.yml"
            write_workflow(
                workflow_path=wf,
                prompts_dir=prompts,
                source_ref="git+https://example.com/x@y",
            )
            content = wf.read_text(encoding="utf-8")

        self.assertIn("cron: '0 8 * * *'", content)
        self.assertIn("cron: '0 9 * * 1'", content)
        self.assertIn("uvx --from git+https://example.com/x@y jules-scheduler tick", content)


if __name__ == "__main__":
    unittest.main()
