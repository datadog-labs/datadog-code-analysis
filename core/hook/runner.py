# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import json
import sys

from core.logger.composite_logger import log


def run(name, handler, rewake=False, event_name=None):
    session_id = "unknown"
    message = None
    data = {}
    try:
        data = json.load(sys.stdin)
        session_id = data.get("session_id", "unknown")
        message = handler(data, session_id)
    except Exception as e:
        log(session_id, f"{name} crashed: {e}")
        sys.exit(0)

    if not message:
        sys.exit(0)

    if rewake:
        print(message, file=sys.stderr)
        sys.exit(2)

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": event_name or data.get("hook_event_name", "PostToolUse"),
                    "additionalContext": message,
                }
            }
        )
    )
    sys.exit(0)
