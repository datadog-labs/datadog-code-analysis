import os
import unittest
from unittest.mock import MagicMock, patch

from core.llm.claude_client import LLMError
from core.review import telemetry_review


class FormatFindingsMessageTest(unittest.TestCase):
    def test_renders_one_line_per_finding(self):
        msg = telemetry_review.format_findings_message(
            [
                {"category": "missing_metric", "file": "a.py", "description": "no metric"},
                {"category": "missing_log", "file": "b.py", "description": "no log"},
            ]
        )
        self.assertIn("- [missing_metric] a.py: no metric", msg)
        self.assertIn("- [missing_log] b.py: no log", msg)

    def test_tolerates_missing_fields(self):
        self.assertIn("- [finding] ?: ", telemetry_review.format_findings_message([{}]))

    def test_always_states_findings_are_suggestions(self):
        msg = telemetry_review.format_findings_message([{"file": "a.py"}])
        self.assertIn("suggestions, not requirements", msg)
        self.assertIn("without the user's go-ahead", msg)


class TempDiffFileTest(unittest.TestCase):
    def test_writes_the_diff_and_removes_it_afterwards(self):
        with telemetry_review._temp_diff_file("diff body", "sid") as path:
            self.assertTrue(os.path.exists(path))
            with open(path) as f:
                self.assertEqual(f.read(), "diff body")
        self.assertFalse(os.path.exists(path))

    def test_removes_the_file_even_when_the_body_raises(self):
        with self.assertRaises(ValueError):
            with telemetry_review._temp_diff_file("x", "sid") as path:
                raise ValueError("boom")
        self.assertFalse(os.path.exists(path))


class RunTest(unittest.TestCase):
    def setUp(self):
        self.enqueue_patch = patch.object(telemetry_review, "enqueue")
        self.mock_enqueue = self.enqueue_patch.start()

    def tearDown(self):
        self.enqueue_patch.stop()

    def _client(self, guidance):
        client = MagicMock()
        client.load_guidance.return_value = guidance
        return client

    def test_returns_none_without_guidance(self):
        with patch.object(telemetry_review, "SkillClient", return_value=self._client(None)), patch.object(
            telemetry_review, "call_claude"
        ) as mock_call:
            self.assertIsNone(telemetry_review.run("sid", "/repo", "diff"))
        mock_call.assert_not_called()
        self.mock_enqueue.assert_not_called()

    def test_returns_findings_and_reports_the_run(self):
        findings = [{"file": "a.py", "category": "missing_metric", "description": "no metric"}]
        with patch.object(
            telemetry_review, "SkillClient", return_value=self._client("GUIDANCE")
        ), patch.object(telemetry_review, "call_claude", return_value={"findings": findings}):
            self.assertEqual(telemetry_review.run("sid", "/repo", "diff"), findings)
        self.mock_enqueue.assert_called_once()

    def test_passes_guidance_and_a_readable_diff_path_to_the_model(self):
        with patch.object(
            telemetry_review, "SkillClient", return_value=self._client("GUIDANCE")
        ), patch.object(telemetry_review, "call_claude", return_value={"findings": []}) as mock_call:
            telemetry_review.run("sid", "/repo", "diff")

        _system, prompt = mock_call.call_args[0][0], mock_call.call_args[0][1]
        self.assertIn("GUIDANCE", prompt)
        self.assertIn(".diff", prompt)
        self.assertEqual(mock_call.call_args[1]["cwd"], "/repo")

    def test_empty_findings_on_llm_failure_still_reports_the_run(self):
        with patch.object(
            telemetry_review, "SkillClient", return_value=self._client("GUIDANCE")
        ), patch.object(telemetry_review, "call_claude", side_effect=LLMError("boom")):
            self.assertEqual(telemetry_review.run("sid", "/repo", "diff"), [])
        self.mock_enqueue.assert_called_once()

    def test_tolerates_a_response_without_findings(self):
        with patch.object(
            telemetry_review, "SkillClient", return_value=self._client("GUIDANCE")
        ), patch.object(telemetry_review, "call_claude", return_value={}):
            self.assertEqual(telemetry_review.run("sid", "/repo", "diff"), [])
