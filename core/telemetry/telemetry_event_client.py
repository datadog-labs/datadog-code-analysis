import json
import time
import uuid

from core.env.config import get_plugin_version
from core.httpclient.datadog_client import DatadogClient, DatadogClientError
from core.logger.composite_logger import log

TELEMETRY_EVENTS_PATH = "/api/unstable/iac-api/coding-plugin/telemetry-events"
RESOURCE_TYPE = "report_telemetry_events_request"


class TelemetryEventClient(DatadogClient):
    def __init__(self, session_id, resolve_credentials):
        super().__init__(session_id, resolve_credentials, timeout=2)

    def send(self, events):
        names = [e["name"] for e in events]
        now = int(time.time())
        attributes = {
            "plugin_version": get_plugin_version(),
            "session_id": self._session_id,
            "events": [
                {
                    "name": e["name"],
                    "metadata": e.get("metadata") or {},
                    "timestamp": e.get("timestamp", now),
                }
                for e in events
            ],
        }

        payload = {"data": {"type": RESOURCE_TYPE, "id": str(uuid.uuid4()), "attributes": attributes}}

        try:
            with self.request(
                TELEMETRY_EVENTS_PATH,
                method="POST",
                data=json.dumps(payload).encode(),
                content_type="application/vnd.api+json",
            ) as resp:
                log(self._session_id, f"reported telemetry events {names} → {resp.status}")
            return True
        except DatadogClientError as e:
            log(self._session_id, f"skipping reporting telemetry events {names}: {e}")
        except Exception as e:
            log(self._session_id, f"failed to report telemetry events {names}: {e}")
        return False
