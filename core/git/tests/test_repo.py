import subprocess
import unittest
from unittest.mock import MagicMock, patch

from core.git import repo


def _proc(returncode, stdout="", stderr=""):
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


class HeadShaTest(unittest.TestCase):
    def test_returns_stripped_sha(self):
        with patch.object(repo, "run", return_value=_proc(0, stdout="sha1\n")):
            self.assertEqual(repo.head_sha("/repo"), "sha1")

    def test_returns_none_on_nonzero_exit(self):
        with patch.object(repo, "run", return_value=_proc(128, stderr="not a repo")):
            self.assertIsNone(repo.head_sha("/repo"))

    def test_returns_none_when_git_is_missing_or_hangs(self):
        for boom in (FileNotFoundError("git"), subprocess.TimeoutExpired(cmd="git", timeout=15)):
            with self.subTest(type(boom).__name__):
                with patch.object(repo, "run", side_effect=boom):
                    self.assertIsNone(repo.head_sha("/repo"))


class ToplevelTest(unittest.TestCase):
    def test_returns_root_on_success(self):
        with patch.object(repo, "run", return_value=_proc(0, stdout="/repo\n")):
            self.assertEqual(repo.toplevel("/repo/sub"), ("/repo", None))

    def test_returns_error_when_not_a_repo(self):
        with patch.object(repo, "run", return_value=_proc(128, stderr="fatal: not a git repository")):
            self.assertEqual(repo.toplevel("/tmp"), (None, "fatal: not a git repository"))


class ResolveTest(unittest.TestCase):
    def test_resolves_root_and_head(self):
        with patch.object(repo, "toplevel", return_value=("/repo", None)), patch.object(
            repo, "head_sha", return_value="sha1"
        ):
            self.assertEqual(repo.resolve("/repo/sub"), (("/repo", "sha1"), None))

    def test_error_when_cwd_not_a_repo(self):
        with patch.object(repo, "toplevel", return_value=(None, "fatal: not a git repository")):
            self.assertEqual(repo.resolve("/tmp"), (None, "fatal: not a git repository"))

    def test_error_when_repo_has_no_commits(self):
        with patch.object(repo, "toplevel", return_value=("/repo", None)), patch.object(
            repo, "head_sha", return_value=None
        ):
            resolved, error = repo.resolve("/repo")
        self.assertIsNone(resolved)
        self.assertIn("/repo", error)


class DiffTest(unittest.TestCase):
    def test_empty_when_base_equals_head(self):
        with patch.object(repo, "run") as mock_run:
            self.assertEqual(repo.diff("/repo", "sha1", "sha1"), "")
        mock_run.assert_not_called()

    def test_returns_stdout(self):
        with patch.object(repo, "run", return_value=_proc(0, stdout="diff body")):
            self.assertEqual(repo.diff("/repo", "a", "b"), "diff body")

    def test_empty_on_nonzero_exit(self):
        with patch.object(repo, "run", return_value=_proc(1, stderr="boom")):
            self.assertEqual(repo.diff("/repo", "a", "b"), "")

    def test_passes_exclude_pathspecs_through(self):
        with patch.object(repo, "run", return_value=_proc(0, stdout="")) as mock_run:
            repo.diff("/repo", "a", "b", [":(exclude)x"])
        self.assertIn(":(exclude)x", mock_run.call_args[0])


class UserEmailTest(unittest.TestCase):
    def test_returns_configured_email(self):
        with patch.object(repo, "run", return_value=_proc(0, stdout="me@example.com\n")):
            self.assertEqual(repo.user_email(), "me@example.com")

    def test_falls_back_to_unknown(self):
        for outcome in (_proc(1), _proc(0, stdout="\n")):
            with self.subTest(outcome.returncode):
                with patch.object(repo, "run", return_value=outcome):
                    self.assertEqual(repo.user_email(), "unknown")

    def test_falls_back_when_git_missing(self):
        with patch.object(repo, "run", side_effect=FileNotFoundError("git")):
            self.assertEqual(repo.user_email(), "unknown")
