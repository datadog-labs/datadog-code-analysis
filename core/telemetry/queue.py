# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

from core.credentials.composite_credential_resolver import get_dd_credentials
from core.logger.composite_logger import log
from core.state.filelock import try_lock
from core.state.session_state import ro_session_state, rw_session_state, session_file
from core.telemetry.telemetry_event_client import TelemetryEventClient

DRAIN_LOCK_SUFFIX = ".drain.lock"


def enqueue(session_id, event):
    with rw_session_state(session_id) as state:
        state.append_pending_event(event)


def drain(session_id):
    """Drains hold their own lock, not the session-state lock: Stop fires every
    turn, so two drains could otherwise read the same queue and submit it twice
    -- while locking the state file would stall the sync hooks that take it to
    claim their one-shot slots, for the length of an HTTP request.

    Only the events actually sent are dropped; the queue is append-only, so
    dropping the leading N can't discard something enqueued while we sent.
    """
    with try_lock(session_file(session_id, DRAIN_LOCK_SUFFIX)) as acquired:
        if not acquired:
            return 0

        pending = ro_session_state(session_id).get_pending_events()
        if not pending:
            return 0

        log(session_id, f"draining {len(pending)} queued telemetry event(s)")
        if not TelemetryEventClient(session_id, get_dd_credentials).send(pending):
            return 0

        with rw_session_state(session_id) as state:
            state.drop_pending_events(len(pending))
        return len(pending)
