#!/usr/bin/env python3
# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.hook.runner import run
from core.state.util import cleanup_old_state
from core.telemetry.queue import drain


def on_stop(data, session_id):
    cleanup_old_state(session_id)
    drain(session_id)


if __name__ == "__main__":
    run("telemetry.py", on_stop)
