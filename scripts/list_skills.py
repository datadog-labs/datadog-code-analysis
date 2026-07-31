#!/usr/bin/env python3
# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.credentials.composite_credential_resolver import get_dd_credentials
from core.logger.composite_logger import log
from core.skills.skill_client import SkillClient, SkillClientError
from core.state.session_state import rw_session_state
from core.telemetry import events
from core.telemetry.telemetry_event_client import TelemetryEventClient


if __name__ == "__main__":
    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID", "unknown")
    try:
        skills = SkillClient(session_id, get_dd_credentials).list_skills()
        for skill in skills:
            print(f"{skill['name']}: {skill['description']}")
        with rw_session_state(session_id) as state:
            state.set_skills_listed(True)
        TelemetryEventClient(session_id, get_dd_credentials).send([events.skills_listed()])
    except SkillClientError as e:
        log(session_id, f"failed to list skills: {e}")
    except Exception as e:
        log(session_id, f"list_skills.py crashed: {e}")
