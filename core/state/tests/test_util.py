# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from core.state.session_state import rw_session_state
from core.state.util import cleanup_old_state


class CleanupOldStateTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.app_home_patch = patch("core.state.session_state.app_home", return_value=self.tmpdir)
        self.app_home_patch.start()

    def tearDown(self):
        self.app_home_patch.stop()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _state_file(self, session_id):
        return os.path.join(self.tmpdir, "state", f"{session_id}.json")

    def test_removes_old_files_when_sampled_in(self):
        with rw_session_state("sid") as state:
            state.set_repo_root("/repo")
        os.utime(self._state_file("sid"), (0, 0))

        with patch("random.random", return_value=0.0):
            cleanup_old_state("other-sid")

        self.assertFalse(os.path.exists(self._state_file("sid")))

    def test_keeps_recent_files(self):
        with rw_session_state("sid") as state:
            state.set_repo_root("/repo")

        with patch("random.random", return_value=0.0):
            cleanup_old_state("other-sid")

        self.assertTrue(os.path.exists(self._state_file("sid")))

    def test_skipped_when_not_sampled_in(self):
        with rw_session_state("sid") as state:
            state.set_repo_root("/repo")
        os.utime(self._state_file("sid"), (0, 0))

        with patch("random.random", return_value=0.99):
            cleanup_old_state("other-sid")

        self.assertTrue(os.path.exists(self._state_file("sid")))
