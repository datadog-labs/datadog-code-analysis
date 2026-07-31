#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.credentials.composite_credential_resolver import get_dd_credentials
from core.logger.composite_logger import log
from core.skills.skill_client import SkillClient, SkillClientError, SkillNotFoundError
from core.state.session_state import rw_session_state
from core.telemetry import events
from core.telemetry.telemetry_event_client import TelemetryEventClient


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: load_skill.py <skill-name>", file=sys.stderr)
        sys.exit(1)

    target = sys.argv[1]
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

    with rw_session_state(session_id) as state:
        state.add_loaded_skill(target)
    TelemetryEventClient(session_id, get_dd_credentials).send(
        [events.skill_loaded(target.replace("/", "__").replace(":", "__"))]
    )

    print(content)
