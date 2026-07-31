#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import SILENT_NUDGE_PREFIX
from core.env.config import get_plugin_root
from core.hook.runner import run
from core.state.session_state import rw_session_state
from core.telemetry import events
from core.telemetry.queue import enqueue


def on_edit(data, session_id):
    with rw_session_state(session_id) as state:
        if state.is_skills_listed() or state.is_edit_nudge_sent():
            return None
        state.set_edit_nudge_sent(True)

    enqueue(session_id, events.edit_nudge_fired())

    plugin_root = get_plugin_root()
    return (
        SILENT_NUDGE_PREFIX + "The user has opted into Datadog coding-time suggestions, but skills haven't "
        f"been listed yet this session. Run `{plugin_root}/scripts/list_skills.py` to see "
        "available Datadog guidance. Judge relevance against the whole task you're working "
        "on, not just the edit that triggered this nudge -- a skill can be irrelevant to this "
        "one change but still apply to the broader feature or fix in progress. Load anything "
        f"relevant at that scope with `{plugin_root}/scripts/load_skill.py <skill-name>` and apply it going forward."
    )


if __name__ == "__main__":
    run("edit_nudge.py", on_edit)
