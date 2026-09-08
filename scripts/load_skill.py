#!/usr/bin/env python3
# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.credentials.composite_credential_resolver import get_dd_credentials
from core.logger.composite_logger import log
from core.skills.skill_client import SkillClient, SkillClientError, SkillNotFoundError
from core.state.session_state import rw_session_state
from core.telemetry import events
from core.telemetry.events import Purpose
from core.telemetry.telemetry_event_client import TelemetryEventClient


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_name")
    parser.add_argument(
        "--purpose",
        type=Purpose,
        choices=list(Purpose),
        default=Purpose.CODING_SESSION,
    )
    args = parser.parse_args()

    target = args.skill_name
    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID", "unknown")
    try:
        skill = SkillClient(session_id, get_dd_credentials).get_skill(target)
        content = skill["content"]
    except SkillNotFoundError:
        print(f"Skill '{target}' not found.", file=sys.stderr)
        sys.exit(1)
    except SkillClientError as e:
        print(f"Failed to load skill '{target}': {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        log(session_id, f"load_skill.py crashed for '{target}': {e}")
        print(f"Failed to load skill '{target}': malformed response", file=sys.stderr)
        sys.exit(1)

    if args.purpose is Purpose.CODING_SESSION:
        with rw_session_state(session_id) as state:
            state.add_loaded_skill(target)
    TelemetryEventClient(session_id, get_dd_credentials).send(
        [events.skill_loaded(target.replace("/", "__").replace(":", "__"), args.purpose)]
    )

    print(content)
