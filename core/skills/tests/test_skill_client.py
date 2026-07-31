import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from core.credentials.types import APIAppKeyCredential
from core.skills.skill_client import SkillClient, SkillClientError, SkillNotFoundError


FAKE_CRED = APIAppKeyCredential(api_key="fake-api-key", app_key="fake-app-key", dd_site="datadoghq.com")


class SkillClientTest(unittest.TestCase):
    def setUp(self):
        self.client = SkillClient("sid", lambda _session_id: FAKE_CRED)

    def _patch_response(self, body):
        return (
            patch("json.load", return_value=body),
            patch.object(self.client, "_urlopen_with_retry", return_value=MagicMock()),
        )

    def test_list_skills_requests_tagged_skills(self):
        body: dict = {"data": {"attributes": {"skills": [{"name": "a", "description": "d", "tags": []}]}}}
        json_patch, urlopen_patch = self._patch_response(body)
        with json_patch, urlopen_patch as mock_urlopen:
            result = self.client.list_skills()

        req = mock_urlopen.call_args[0][0]
        self.assertTrue(req.full_url.startswith("https://api.datadoghq.com/api/unstable/iac-api/skills?"))
        self.assertIn("coding_telemetry_skill", req.full_url)
        self.assertEqual(req.get_header("Dd-api-key"), "fake-api-key")
        self.assertEqual(req.get_header("Dd-application-key"), "fake-app-key")
        self.assertEqual(result, [{"name": "a", "description": "d", "tags": []}])

    def test_get_skill_requests_named_skill(self):
        body: dict = {
            "data": {"attributes": {"name": "a", "description": "d", "tags": [], "content": "guidance"}}
        }
        json_patch, urlopen_patch = self._patch_response(body)
        with json_patch, urlopen_patch as mock_urlopen:
            result = self.client.get_skill("my/skill")

        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, "https://api.datadoghq.com/api/unstable/iac-api/skills/my%2Fskill")
        self.assertEqual(result["content"], "guidance")

    def test_reuses_credentials_across_calls(self):
        calls = []

        def provider(session_id):
            calls.append(session_id)
            return FAKE_CRED

        client = SkillClient("sid", provider)
        body: dict = {"data": {"attributes": {"skills": []}}}
        with patch("json.load", return_value=body), patch.object(
            client, "_urlopen_with_retry", return_value=MagicMock()
        ):
            client.list_skills()
            client.get_skill("a")
        self.assertEqual(calls, ["sid"])

    def test_no_credentials_raises_skill_client_error(self):
        self.client = SkillClient("sid", lambda _session_id: None)
        with self.assertRaises(SkillClientError):
            self.client.list_skills()

    def test_404_raises_skill_not_found_error(self):
        with patch.object(
            self.client,
            "_urlopen_with_retry",
            side_effect=urllib.error.HTTPError("http://x", 404, "not found", {}, None),  # type: ignore[arg-type]
        ):
            with self.assertRaises(SkillNotFoundError):
                self.client.get_skill("missing")

    def test_non_404_http_error_raises_skill_client_error(self):
        with patch.object(
            self.client,
            "_urlopen_with_retry",
            side_effect=urllib.error.HTTPError("http://x", 500, "server error", {}, None),  # type: ignore[arg-type]
        ):
            with self.assertRaises(SkillClientError) as ctx:
                self.client.get_skill("broken")
        self.assertNotIsInstance(ctx.exception, SkillNotFoundError)

    def test_request_failure_raises_skill_client_error(self):
        with patch.object(self.client, "_urlopen_with_retry", side_effect=Exception("boom")):
            with self.assertRaises(SkillClientError):
                self.client.list_skills()


class LoadGuidanceTest(unittest.TestCase):
    def setUp(self):
        self.client = SkillClient("sid", lambda _session_id: FAKE_CRED)

    def test_concatenates_each_skill_under_its_name(self):
        with patch.object(
            self.client, "list_skills", return_value=[{"name": "alpha"}, {"name": "beta"}]
        ), patch.object(self.client, "get_skill", side_effect=lambda n: {"name": n, "content": n.upper()}):
            guidance = self.client.load_guidance()
        self.assertIn("## alpha\nALPHA", guidance)
        self.assertIn("## beta\nBETA", guidance)

    def test_none_when_no_skills_exist(self):
        with patch.object(self.client, "list_skills", return_value=[]):
            self.assertIsNone(self.client.load_guidance())

    def test_none_when_listing_fails(self):
        with patch.object(self.client, "list_skills", side_effect=SkillClientError("boom")):
            self.assertIsNone(self.client.load_guidance())

    def test_skips_the_skills_that_fail_to_load(self):
        def get_skill(name):
            if name == "bad":
                raise SkillClientError("nope")
            return {"name": name, "content": "A"}

        with patch.object(
            self.client, "list_skills", return_value=[{"name": "ok"}, {"name": "bad"}]
        ), patch.object(self.client, "get_skill", side_effect=get_skill):
            self.assertEqual(self.client.load_guidance(), "## ok\nA")

    def test_none_when_every_skill_fails_to_load(self):
        with patch.object(self.client, "list_skills", return_value=[{"name": "bad"}]), patch.object(
            self.client, "get_skill", side_effect=SkillClientError("nope")
        ):
            self.assertIsNone(self.client.load_guidance())
