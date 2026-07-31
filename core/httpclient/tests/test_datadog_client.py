import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from core.credentials.types import APIAppKeyCredential
from core.httpclient.datadog_client import DatadogClient, DatadogClientError


FAKE_CRED = APIAppKeyCredential(api_key="fake-api-key", app_key="fake-app-key", dd_site="datadoghq.com")


class RequestTest(unittest.TestCase):
    def setUp(self):
        self.cred: APIAppKeyCredential | None = FAKE_CRED
        self.calls = []

    def _provider(self, session_id):
        self.calls.append(session_id)
        return self.cred

    def _request(self, client, *args, **kwargs):
        with patch.object(client, "_urlopen_with_retry", return_value=MagicMock()) as mock_urlopen:
            client.request(*args, **kwargs)
        return mock_urlopen.call_args[0][0]

    def test_builds_url_from_host_site_and_path(self):
        req = self._request(DatadogClient("sid", self._provider), "/v1/things")
        self.assertEqual(req.full_url, "https://api.datadoghq.com/v1/things")

    def test_uses_overridden_host(self):
        req = self._request(DatadogClient("sid", self._provider, host="http-intake.logs"), "/v1/logs")
        self.assertEqual(req.full_url, "https://http-intake.logs.datadoghq.com/v1/logs")

    def test_includes_app_key_by_default(self):
        req = self._request(DatadogClient("sid", self._provider), "/v1/things")
        self.assertEqual(req.get_header("Dd-api-key"), "fake-api-key")
        self.assertEqual(req.get_header("Dd-application-key"), "fake-app-key")

    def test_omits_app_key_when_disabled(self):
        req = self._request(DatadogClient("sid", self._provider, include_app_key=False), "/v1/things")
        self.assertEqual(req.get_header("Dd-api-key"), "fake-api-key")
        self.assertIsNone(req.get_header("Dd-application-key"))

    def test_sets_method_body_and_content_type(self):
        req = self._request(
            DatadogClient("sid", self._provider),
            "/v1/things",
            method="POST",
            data=b"{}",
            content_type="application/json",
        )
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.data, b"{}")
        self.assertEqual(req.get_header("Content-type"), "application/json")

    def test_omits_content_type_when_not_given(self):
        req = self._request(DatadogClient("sid", self._provider), "/v1/things")
        self.assertIsNone(req.get_header("Content-type"))

    def test_raises_when_no_credentials_available(self):
        self.cred = None
        with self.assertRaises(DatadogClientError):
            DatadogClient("sid", self._provider).request("/v1/things")

    def test_resolves_credentials_once_across_requests(self):
        client = DatadogClient("sid", self._provider)
        with patch.object(client, "_urlopen_with_retry", return_value=MagicMock()):
            client.request("/v1/things")
            client.request("/v1/others")
        self.assertEqual(self.calls, ["sid"])


class UrlopenWithRetryTest(unittest.TestCase):
    def setUp(self):
        self.client = DatadogClient("sid", lambda s: FAKE_CRED, timeout=5)
        self.req = MagicMock()

    def test_returns_response_on_first_success(self):
        response = MagicMock()
        with patch("urllib.request.urlopen", return_value=response) as mock_urlopen:
            result = self.client._urlopen_with_retry(self.req)
        self.assertIs(result, response)
        mock_urlopen.assert_called_once_with(self.req, timeout=5)

    def test_retries_on_url_error_then_succeeds(self):
        response = MagicMock()
        with patch(
            "urllib.request.urlopen", side_effect=[urllib.error.URLError("boom"), response]
        ) as mock_urlopen, patch("time.sleep") as mock_sleep:
            result = self.client._urlopen_with_retry(self.req)
        self.assertIs(result, response)
        self.assertEqual(mock_urlopen.call_count, 2)
        mock_sleep.assert_called_once()

    def test_raises_url_error_after_exhausting_retries(self):
        with patch(
            "urllib.request.urlopen", side_effect=urllib.error.URLError("boom")
        ) as mock_urlopen, patch("time.sleep"):
            with self.assertRaises(urllib.error.URLError):
                self.client._urlopen_with_retry(self.req)
        self.assertEqual(mock_urlopen.call_count, 3)

    def test_does_not_retry_on_http_error(self):
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError("http://x", 404, "not found", {}, None),  # type: ignore[arg-type]
        ) as mock_urlopen:
            with self.assertRaises(urllib.error.HTTPError):
                self.client._urlopen_with_retry(self.req)
        mock_urlopen.assert_called_once()
