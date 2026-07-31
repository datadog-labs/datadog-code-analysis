# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import shutil
import tempfile
import unittest
from unittest.mock import patch

import capture_baseline
from core.state.session_state import ro_session_state, rw_session_state

EDIT = {"tool_input": {"file_path": "/repo/sub/x.py"}}


class OnFileModifiedTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.app_home_patch = patch("core.state.session_state.app_home", return_value=self.tmpdir)
        self.app_home_patch.start()

    def tearDown(self):
        self.app_home_patch.stop()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_locks_onto_the_repo_holding_the_edited_file(self):
        with patch.object(
            capture_baseline.repo, "resolve", return_value=(("/repo", "sha1"), None)
        ) as mock_resolve:
            capture_baseline.on_file_modified(EDIT, "sid")

        mock_resolve.assert_called_once_with("/repo/sub")
        state = ro_session_state("sid")
        self.assertEqual(state.get_repo_root(), "/repo")
        self.assertEqual(state.get_baseline_sha(), "sha1")

    def test_does_not_relock_once_set(self):
        with rw_session_state("sid") as state:
            state.set_repo_root("/repo")
            state.set_baseline_sha("sha1")

        with patch.object(capture_baseline.repo, "resolve") as mock_resolve:
            capture_baseline.on_file_modified({"tool_input": {"file_path": "/other/y.py"}}, "sid")

        mock_resolve.assert_not_called()
        state = ro_session_state("sid")
        self.assertEqual(state.get_repo_root(), "/repo")
        self.assertEqual(state.get_baseline_sha(), "sha1")

    def test_writes_nothing_when_the_repo_cannot_be_resolved(self):
        with patch.object(
            capture_baseline.repo, "resolve", return_value=(None, "fatal: not a git repository")
        ):
            capture_baseline.on_file_modified(EDIT, "sid")

        self.assertIsNone(ro_session_state("sid").get_repo_root())

    def test_ignores_payloads_without_a_file_path(self):
        for payload in ({}, {"tool_input": {}}, {"tool_input": {"file_path": ""}}):
            with self.subTest(payload):
                with patch.object(capture_baseline.repo, "resolve") as mock_resolve:
                    capture_baseline.on_file_modified(payload, "sid")
                mock_resolve.assert_not_called()
