#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import SILENT_NUDGE_PREFIX
from core.credentials.cached_user_config_credential_resolver import configure_user_cfg_cred_cache
from core.env.config import (
    get_plugin_root,
    on_commit_telemetry_review_enabled,
    resource_suggestions_enabled,
)
from core.hook.runner import run
from core.logger.composite_logger import log
from core.telemetry import events
from core.telemetry.queue import enqueue


def on_session_start(data, session_id):
    configure_user_cfg_cred_cache(session_id)
    enqueue(
        session_id,
        events.session_started(on_commit_telemetry_review_enabled(), resource_suggestions_enabled()),
    )
    plugin_root = get_plugin_root()
    return (
        SILENT_NUDGE_PREFIX + "The user has opted into Datadog coding-time suggestions. "
        "Before writing a plan or making any code changes, run "
        f"`{plugin_root}/scripts/list_skills.py` to see available Datadog guidance. "
        f"Then run `{plugin_root}/scripts/load_skill.py <skill-name>` to load any that may be relevant. "
        "Apply the loaded guidance to your plan or implementation."
    )


if __name__ == "__main__":
    run("session_start.py", on_session_start, event_name="SessionStart")
