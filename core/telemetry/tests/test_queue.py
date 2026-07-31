# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.state.filelock import try_lock
from core.state.session_state import ro_session_state, rw_session_state, session_file
from core.telemetry import events
from core.telemetry.queue import DRAIN_LOCK_SUFFIX, drain, enqueue


class QueueTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.app_home_patch = patch("core.state.session_state.app_home", return_value=self.tmpdir)
        self.app_home_patch.start()

    def tearDown(self):
        self.app_home_patch.stop()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _pending(self):
        return ro_session_state("sid").get_pending_events()

    def test_enqueue_appends_in_order(self):
        enqueue("sid", events.edit_nudge_fired())
        enqueue("sid", events.reviewer_ran(2))
        self.assertEqual([e["name"] for e in self._pending()], ["edit_nudge_fired", "reviewer_ran"])

    def test_drain_with_empty_queue_sends_nothing(self):
        with patch("core.telemetry.queue.TelemetryEventClient") as client:
            self.assertEqual(drain("sid"), 0)
        client.assert_not_called()

    def test_successful_drain_sends_batch_and_clears(self):
        enqueue("sid", events.edit_nudge_fired())
        enqueue("sid", events.coding_session_started())

        with patch("core.telemetry.queue.TelemetryEventClient") as client:
            client.return_value.send.return_value = True
            self.assertEqual(drain("sid"), 2)

        sent = client.return_value.send.call_args[0][0]
        self.assertEqual([e["name"] for e in sent], ["edit_nudge_fired", "coding_session_started"])
        self.assertEqual(self._pending(), [])

    def test_failed_drain_leaves_queue_for_retry(self):
        enqueue("sid", events.edit_nudge_fired())

        with patch("core.telemetry.queue.TelemetryEventClient") as client:
            client.return_value.send.return_value = False
            self.assertEqual(drain("sid"), 0)
        self.assertEqual([e["name"] for e in self._pending()], ["edit_nudge_fired"])

        with patch("core.telemetry.queue.TelemetryEventClient") as client:
            client.return_value.send.return_value = True
            self.assertEqual(drain("sid"), 1)
        self.assertEqual(self._pending(), [])

    def test_concurrent_drain_is_skipped_rather_than_duplicating(self):
        enqueue("sid", events.edit_nudge_fired())

        with try_lock(session_file("sid", DRAIN_LOCK_SUFFIX)) as held:
            self.assertTrue(held)
            with patch("core.telemetry.queue.TelemetryEventClient") as client:
                self.assertEqual(drain("sid"), 0)
            client.assert_not_called()

        self.assertEqual([e["name"] for e in self._pending()], ["edit_nudge_fired"])

    def test_event_enqueued_during_send_survives_the_drop(self):
        enqueue("sid", events.edit_nudge_fired())

        def send_then_enqueue(batch):
            enqueue("sid", events.reviewer_ran(1))
            return True

        with patch("core.telemetry.queue.TelemetryEventClient") as client:
            client.return_value.send.side_effect = send_then_enqueue
            self.assertEqual(drain("sid"), 1)

        self.assertEqual([e["name"] for e in self._pending()], ["reviewer_ran"])


class TryLockTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_second_acquisition_fails_while_first_is_held(self):
        path = str(Path(self.tmpdir) / "x.lock")
        with try_lock(path) as first:
            self.assertTrue(first)
            with try_lock(path) as second:
                self.assertFalse(second)

    def test_lock_is_reusable_after_release(self):
        path = str(Path(self.tmpdir) / "x.lock")
        with try_lock(path) as first:
            self.assertTrue(first)
        with try_lock(path) as again:
            self.assertTrue(again)
