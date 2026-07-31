# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from core.state.session_state import (
    ReadOnlySessionState,
    ReadWriteSessionState,
    ro_session_state,
    rw_session_state,
)


class ReadOnlySessionStateTest(unittest.TestCase):
    def test_defaults_on_empty_state(self):
        state = ReadOnlySessionState({})
        self.assertFalse(state.is_skills_listed())
        self.assertFalse(state.is_edit_nudge_sent())
        self.assertFalse(state.is_coding_session_started())
        self.assertFalse(state.is_resource_nudge_sent())
        self.assertFalse(state.is_feedback_prompted())
        self.assertFalse(state.is_resolution_feedback_prompted())
        self.assertFalse(state.is_review_done())
        self.assertIsNone(state.get_repo_root())
        self.assertIsNone(state.get_baseline_sha())
        self.assertIsNone(state.get_review_sha())
        self.assertEqual(state.get_loaded_skills(), [])
        self.assertIsNone(state.get_review_findings())

    def test_reads_populated_fields(self):
        state = ReadOnlySessionState(
            {
                "skills_listed": True,
                "repo_root": "/repo",
                "baseline_sha": "sha1",
                "loaded_skills": ["a", "b"],
                "review_findings": [{"file": "x.py"}],
            }
        )
        self.assertTrue(state.is_skills_listed())
        self.assertEqual(state.get_repo_root(), "/repo")
        self.assertEqual(state.get_baseline_sha(), "sha1")
        self.assertEqual(state.get_loaded_skills(), ["a", "b"])
        self.assertEqual(state.get_review_findings(), [{"file": "x.py"}])

    def test_has_no_setters(self):
        state = ReadOnlySessionState({})
        self.assertFalse(hasattr(state, "set_repo_root"))


class ReadWriteSessionStateTest(unittest.TestCase):
    def test_setters_write_through_to_data(self):
        data: dict = {}
        state = ReadWriteSessionState(data)

        state.set_skills_listed(True)
        state.set_edit_nudge_sent(True)
        state.set_coding_session_started(True)
        state.set_resource_nudge_sent(True)
        state.set_feedback_prompted(True)
        state.set_resolution_feedback_prompted(True)
        state.set_review_done(True)
        state.set_repo_root("/repo")
        state.set_baseline_sha("sha1")
        state.set_review_sha("sha2")
        state.set_review_findings([{"file": "x.py"}])

        self.assertEqual(
            data,
            {
                "skills_listed": True,
                "edit_nudge_sent": True,
                "coding_session_started": True,
                "resource_nudge_sent": True,
                "feedback_prompted": True,
                "resolution_feedback_prompted": True,
                "review_done": True,
                "repo_root": "/repo",
                "baseline_sha": "sha1",
                "review_sha": "sha2",
                "review_findings": [{"file": "x.py"}],
            },
        )

    def test_add_loaded_skill_appends_new_names(self):
        data: dict = {}
        state = ReadWriteSessionState(data)

        state.add_loaded_skill("skill-a")
        state.add_loaded_skill("skill-b")

        self.assertEqual(data["loaded_skills"], ["skill-a", "skill-b"])

    def test_add_loaded_skill_does_not_duplicate(self):
        data = {"loaded_skills": ["skill-a"]}
        state = ReadWriteSessionState(data)

        state.add_loaded_skill("skill-a")

        self.assertEqual(data["loaded_skills"], ["skill-a"])

    def test_inherits_read_only_getters(self):
        state = ReadWriteSessionState({"repo_root": "/repo"})
        self.assertEqual(state.get_repo_root(), "/repo")


class StateFileTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.app_home_patch = patch("core.state.session_state.app_home", return_value=self.tmpdir)
        self.app_home_patch.start()

    def tearDown(self):
        self.app_home_patch.stop()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _state_file(self, session_id):
        return os.path.join(self.tmpdir, "state", f"{session_id}.json")


class RoSessionStateTest(StateFileTestCase):
    def test_returns_empty_view_when_no_file_exists(self):
        state = ro_session_state("sid")
        self.assertIsNone(state.get_repo_root())

    def test_reads_persisted_state(self):
        with rw_session_state("sid") as state:
            state.set_repo_root("/repo")

        self.assertEqual(ro_session_state("sid").get_repo_root(), "/repo")


class RwSessionStateTest(StateFileTestCase):
    def test_yields_read_write_view_and_persists_on_clean_exit(self):
        with rw_session_state("sid") as state:
            self.assertIsInstance(state, ReadWriteSessionState)
            state.set_repo_root("/repo")

        self.assertEqual(ro_session_state("sid").get_repo_root(), "/repo")

    def test_does_not_persist_changes_on_exception(self):
        with rw_session_state("sid") as state:
            state.set_repo_root("/repo")

        with self.assertRaises(ValueError):
            with rw_session_state("sid") as state:
                state.set_repo_root("/other-repo")
                raise ValueError("boom")

        self.assertEqual(ro_session_state("sid").get_repo_root(), "/repo")

    def test_sees_prior_writes_on_reopen(self):
        with rw_session_state("sid") as state:
            state.set_repo_root("/repo")

        with rw_session_state("sid") as state:
            self.assertEqual(state.get_repo_root(), "/repo")
            state.set_baseline_sha("sha1")

        with rw_session_state("sid") as state:
            self.assertEqual(state.get_repo_root(), "/repo")
            self.assertEqual(state.get_baseline_sha(), "sha1")
