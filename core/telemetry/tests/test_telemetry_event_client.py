import json
import unittest
from unittest.mock import MagicMock, patch

from core.credentials.types import APIAppKeyCredential
from core.telemetry import events, telemetry_event_client
from core.telemetry.telemetry_event_client import TelemetryEventClient

FAKE_CRED = APIAppKeyCredential(api_key="fake-api-key", app_key="fake-app-key", dd_site="datadoghq.com")

EVENT_CASES = [
    (
        events.session_started(True, True),
        "session_started",
        {"on_commit_telemetry_review_enabled": True, "resource_suggestions_enabled": True},
    ),
    (events.coding_session_started(), "coding_session_started", {}),
    (events.skills_listed(), "skills_listed", {}),
    (events.skill_loaded("my-skill"), "skill_loaded", {"skill_name": "my-skill"}),
    (events.edit_nudge_fired(), "edit_nudge_fired", {}),
    (
        events.ddog_resource_nudge_fired("notebook"),
        "ddog_resource_nudge_fired",
        {"resource_type": "notebook"},
    ),
    (events.reviewer_ran(3), "reviewer_ran", {"findings_count": 3}),
    (
        events.agent_feedback_submitted("my-skill", True, telemetry_added=True, telemetry_adjusted=True),
        "agent_feedback_submitted",
        {
            "skill_name": "my-skill",
            "skill_applies": True,
            "telemetry_added": True,
            "telemetry_removed": False,
            "telemetry_adjusted": True,
        },
    ),
    (
        events.agent_feedback_submitted_post_review("all"),
        "agent_feedback_submitted_post_review",
        {"resolved": "all"},
    ),
]


def _mock_response(status=202):
    resp = MagicMock()
    resp.__enter__.return_value.status = status
    return resp


class EventBuilderTest(unittest.TestCase):
    def test_every_builder_produces_name_metadata_and_timestamp(self):
        for event, expected_name, expected_metadata in EVENT_CASES:
            with self.subTest(expected_name):
                self.assertEqual(event["name"], expected_name)
                self.assertEqual(event["metadata"], expected_metadata)
                self.assertIsInstance(event["timestamp"], int)


class TelemetryEventClientTest(unittest.TestCase):
    def setUp(self):
        self.get_plugin_version_patch = patch.object(
            telemetry_event_client, "get_plugin_version", return_value="1.2.3"
        )
        self.get_plugin_version_patch.start()
        self.client = TelemetryEventClient("sid", lambda _session_id: FAKE_CRED)

    def tearDown(self):
        self.get_plugin_version_patch.stop()

    def test_no_credentials_skips_request_and_reports_failure(self):
        self.client = TelemetryEventClient("sid", lambda _session_id: None)
        with patch.object(self.client, "_urlopen_with_retry") as mock_urlopen:
            self.assertFalse(self.client.send([events.edit_nudge_fired()]))
        mock_urlopen.assert_not_called()

    def test_request_uses_credential_site_and_keys(self):
        with patch.object(self.client, "_urlopen_with_retry", return_value=_mock_response()) as mock_urlopen:
            self.assertTrue(self.client.send([events.session_started(True, True)]))

        req = mock_urlopen.call_args[0][0]
        self.assertEqual(
            req.full_url, "https://api.datadoghq.com/api/unstable/iac-api/coding-plugin/telemetry-events"
        )
        self.assertEqual(req.get_header("Dd-api-key"), "fake-api-key")
        self.assertEqual(req.get_header("Dd-application-key"), "fake-app-key")
        self.assertEqual(req.get_header("Content-type"), "application/vnd.api+json")

    def test_request_payload_shape(self):
        with patch.object(self.client, "_urlopen_with_retry", return_value=_mock_response()) as mock_urlopen:
            self.client.send([events.skill_loaded("my-skill")])

        attributes = json.loads(mock_urlopen.call_args[0][0].data.decode())["data"]["attributes"]
        self.assertEqual(attributes["session_id"], "sid")
        self.assertEqual(attributes["plugin_version"], "1.2.3")
        self.assertEqual(attributes["events"][0]["name"], "skill_loaded")
        self.assertEqual(attributes["events"][0]["metadata"], {"skill_name": "my-skill"})

    def test_batches_multiple_events_into_one_request(self):
        batch = [events.edit_nudge_fired(), events.coding_session_started(), events.reviewer_ran(2)]
        with patch.object(self.client, "_urlopen_with_retry", return_value=_mock_response()) as mock_urlopen:
            self.client.send(batch)

        mock_urlopen.assert_called_once()
        sent = json.loads(mock_urlopen.call_args[0][0].data.decode())["data"]["attributes"]["events"]
        self.assertEqual(
            [e["name"] for e in sent], ["edit_nudge_fired", "coding_session_started", "reviewer_ran"]
        )

    def test_preserves_enqueue_time_rather_than_send_time(self):
        event = events.edit_nudge_fired()
        event["timestamp"] = 1234567890
        with patch.object(self.client, "_urlopen_with_retry", return_value=_mock_response()) as mock_urlopen:
            self.client.send([event])

        sent = json.loads(mock_urlopen.call_args[0][0].data.decode())["data"]["attributes"]["events"][0]
        self.assertEqual(sent["timestamp"], 1234567890)

    def test_urlopen_failure_reports_failure_without_raising(self):
        with patch.object(self.client, "_urlopen_with_retry", side_effect=Exception("boom")):
            self.assertFalse(self.client.send([events.edit_nudge_fired()]))
