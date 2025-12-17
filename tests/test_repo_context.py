import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.append(str(Path(__file__).parent.parent / "src"))

from jules_scheduler.repo_context import detect_repo


class TestRepoContext(unittest.TestCase):
    def test_detect_repo_from_env(self):
        with patch.dict("os.environ", {"GITHUB_REPOSITORY": "octo/hello"}, clear=True):
            owner, repo = detect_repo(Path("."))
        self.assertEqual((owner, repo), ("octo", "hello"))

    def test_detect_repo_from_overrides(self):
        owner, repo = detect_repo(Path("."), owner="a", repo="b")
        self.assertEqual((owner, repo), ("a", "b"))

    def test_detect_repo_fallback_git(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch("subprocess.run") as run:
                run.return_value.stdout = "https://github.com/octo/hello.git\n"
                run.return_value.returncode = 0
                owner, repo = detect_repo(root)
        self.assertEqual((owner, repo), ("octo", "hello"))


if __name__ == "__main__":
    unittest.main()
