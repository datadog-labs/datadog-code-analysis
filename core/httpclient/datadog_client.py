import time
import urllib.error
import urllib.request

RETRY_BACKOFFS = (0.3, 0.6)


class DatadogClientError(Exception):
    pass


class DatadogClient:
    def __init__(self, session_id, resolve_credentials, host="api", include_app_key=True, timeout=10):
        self._session_id = session_id
        self._resolve_credentials = resolve_credentials
        self._cred = None
        self._host = host
        self._include_app_key = include_app_key
        self._timeout = timeout

    def _credentials(self):
        if self._cred is None:
            self._cred = self._resolve_credentials(self._session_id)
        return self._cred

    def _headers(self, cred, content_type):
        headers = {"DD-API-KEY": cred.api_key}
        if self._include_app_key:
            headers["DD-APPLICATION-KEY"] = cred.app_key
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def request(self, path, method="GET", data=None, content_type=None):
        cred = self._credentials()
        if cred is None:
            raise DatadogClientError("no credentials available")
        req = urllib.request.Request(
            f"https://{self._host}.{cred.dd_site}{path}",
            data=data,
            headers=self._headers(cred, content_type),
            method=method,
        )
        return self._urlopen_with_retry(req)

    def _urlopen_with_retry(self, req):
        for backoff in (*RETRY_BACKOFFS, None):
            try:
                return urllib.request.urlopen(req, timeout=self._timeout)
            except urllib.error.HTTPError:
                raise
            except urllib.error.URLError:
                if backoff is None:
                    raise
                time.sleep(backoff)
