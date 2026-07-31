# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from core.logger.filesystem_logger import FilesystemLogger


class FilesystemLoggerTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.gettempdir_patch = patch("tempfile.gettempdir", return_value=self.tmpdir)
        self.gettempdir_patch.start()
        self.logger = FilesystemLogger()

    def tearDown(self):
        self.gettempdir_patch.stop()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _log_path(self, session_id):
        return os.path.join(self.tmpdir, f"dd-code-analysis-plugin-{session_id}.log")

    def test_writes_message_to_session_log_file(self):
        self.logger.log("sid", "hello world")

        with open(self._log_path("sid")) as f:
            contents = f.read()
        self.assertIn("hello world", contents)
        self.assertEqual(os.stat(self._log_path("sid")).st_mode & 0o777, 0o600)

    def test_appends_across_multiple_calls(self):
        self.logger.log("sid", "first")
        self.logger.log("sid", "second")

        with open(self._log_path("sid")) as f:
            lines = f.read().splitlines()
        self.assertEqual(len(lines), 2)

    def test_isolates_by_session_id(self):
        self.logger.log("sid-a", "for a")
        self.logger.log("sid-b", "for b")

        with open(self._log_path("sid-a")) as f:
            self.assertIn("for a", f.read())
        with open(self._log_path("sid-b")) as f:
            self.assertIn("for b", f.read())

    def test_never_raises_on_failure(self):
        with patch("os.open", side_effect=OSError("boom")):
            self.logger.log("sid", "hello")
