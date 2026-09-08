# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import datetime
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.plugin_sessions import (
    PLUGIN_SESSION_START_NUDGE,
    default_projects_dir,
    has_plugin_session_start_nudge,
    list_for_preview,
    list_for_review,
    recent_transcripts,
    transcript_created_at,
)


class PluginSessionsTestCase(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.projects_dir = self.root / "projects"
        self.state_dir = self.root / "state"
        self.projects_dir.mkdir()
        self.state_dir.mkdir()

    def tearDown(self):
        self.tempdir.cleanup()

    def write_transcript(self, project, session_id, records, modified_at=None):
        project_dir = self.projects_dir / project
        project_dir.mkdir(exist_ok=True)
        path = project_dir / f"{session_id}.jsonl"
        lines = [record if isinstance(record, str) else json.dumps(record) for record in records]
        path.write_text("\n".join(lines) + "\n")
        if modified_at is not None:
            os.utime(path, (modified_at, modified_at))
        return path

    def write_state(self, session_id):
        path = self.state_dir / f"{session_id}.json"
        path.write_text("{}")
        return path


class DefaultProjectsDirTest(unittest.TestCase):
    def test_uses_claude_config_dir_when_set(self):
        with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": "/custom/claude"}, clear=True):
            self.assertEqual(default_projects_dir(), os.path.join("/custom/claude", "projects"))

    def test_falls_back_to_claude_directory_in_home(self):
        with patch.dict(os.environ, {}, clear=True), patch(
            "scripts.plugin_sessions.os.path.expanduser", return_value="/home/user"
        ):
            self.assertEqual(default_projects_dir(), os.path.join("/home/user", "projects"))


class TranscriptCreatedAtTest(PluginSessionsTestCase):
    def test_returns_first_valid_recorded_timestamp(self):
        path = self.write_transcript(
            "project",
            "session",
            [
                "not json",
                {"type": "file-history-snapshot"},
                {"timestamp": 123},
                {"timestamp": "invalid"},
                {"timestamp": "2026-09-05T12:34:56.789Z"},
                {"timestamp": "2025-01-01T00:00:00Z"},
            ],
        )

        expected = datetime.datetime(2026, 9, 5, 12, 34, 56, 789000, tzinfo=datetime.timezone.utc)
        self.assertEqual(transcript_created_at(str(path)), expected.timestamp())

    def test_treats_timestamp_without_timezone_as_utc(self):
        path = self.write_transcript("project", "session", [{"timestamp": "2026-09-05T12:00:00"}])
        expected = datetime.datetime(2026, 9, 5, 12, tzinfo=datetime.timezone.utc)
        self.assertEqual(transcript_created_at(str(path)), expected.timestamp())

    def test_returns_none_without_a_valid_timestamp(self):
        path = self.write_transcript("project", "session", [{"type": "metadata"}])
        self.assertIsNone(transcript_created_at(str(path)))
        self.assertIsNone(transcript_created_at(str(self.root / "missing.jsonl")))


class RecentTranscriptsTest(PluginSessionsTestCase):
    def test_orders_by_creation_time_and_deduplicates_sessions(self):
        old = self.write_transcript(
            "project-a",
            "old",
            [{"timestamp": "2025-01-01T00:00:00Z"}],
            modified_at=2_000_000_000,
        )
        new = self.write_transcript(
            "project-a",
            "new",
            [{"timestamp": "2026-01-01T00:00:00Z"}],
            modified_at=1,
        )
        duplicate = self.write_transcript(
            "project-b",
            "old",
            [{"timestamp": "2025-02-01T00:00:00Z"}],
        )
        self.write_transcript("project-a", "current", [{"timestamp": "2027-01-01T00:00:00Z"}])
        self.write_transcript("project-a", "no-timestamp", [{"type": "metadata"}])

        result = recent_transcripts(str(self.projects_dir), "current")

        self.assertEqual(result, [("new", str(new)), ("old", str(duplicate))])
        self.assertNotEqual(str(old), str(duplicate))


class ListForReviewTest(PluginSessionsTestCase):
    def test_returns_only_sessions_with_state_up_to_limit(self):
        newest = self.write_transcript("project", "newest", [{"timestamp": "2026-03-01T00:00:00Z"}])
        self.write_transcript("project", "without-state", [{"timestamp": "2026-02-01T00:00:00Z"}])
        older = self.write_transcript("project", "older", [{"timestamp": "2026-01-01T00:00:00Z"}])
        newest_state = self.write_state("newest")
        older_state = self.write_state("older")

        result = list_for_review(2, str(self.projects_dir), str(self.state_dir))["candidates"]

        self.assertEqual(
            result,
            [
                {
                    "session_id": "newest",
                    "transcript_path": str(newest),
                    "state_path": str(newest_state),
                },
                {
                    "session_id": "older",
                    "transcript_path": str(older),
                    "state_path": str(older_state),
                },
            ],
        )


class ListForPreviewTest(PluginSessionsTestCase):
    def test_nudge_detection_distinguishes_absent_present_and_unreadable(self):
        without_nudge = self.write_transcript("project", "without", [{"message": "hello"}])
        with_nudge = self.write_transcript(
            "project", "with", [{"message": f"prefix {PLUGIN_SESSION_START_NUDGE} suffix"}]
        )

        self.assertFalse(has_plugin_session_start_nudge(str(without_nudge)))
        self.assertTrue(has_plugin_session_start_nudge(str(with_nudge)))
        self.assertIsNone(has_plugin_session_start_nudge(str(self.root / "missing.jsonl")))

    def test_skips_plugin_sessions_and_fills_limit_from_older_sessions(self):
        self.write_transcript(
            "project",
            "plugin",
            [
                {"timestamp": "2026-04-01T00:00:00Z"},
                {"message": PLUGIN_SESSION_START_NUDGE},
            ],
        )
        newest = self.write_transcript("project", "newest", [{"timestamp": "2026-03-01T00:00:00Z"}])
        older = self.write_transcript("project", "older", [{"timestamp": "2026-02-01T00:00:00Z"}])

        result = list_for_preview(2, str(self.projects_dir))["candidates"]

        self.assertEqual(
            result,
            [
                {"session_id": "newest", "transcript_path": str(newest)},
                {"session_id": "older", "transcript_path": str(older)},
            ],
        )
