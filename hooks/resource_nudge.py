#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import SILENT_NUDGE_PREFIX
from core.env.config import resource_suggestions_enabled
from core.git import repo
from core.hook.runner import run
from core.logger.composite_logger import log
from core.state.session_state import ro_session_state, rw_session_state
from core.telemetry import events
from core.telemetry.queue import enqueue

NOTEBOOK_NUDGE = (
    SILENT_NUDGE_PREFIX + "The user has opted into Datadog coding time suggestions. This session just "
    "committed new code. If the changeset adds a new feature with telemetry sent to "
    "Datadog (metrics, logs, traces), and you have a way to create Datadog Notebooks "
    "(Datadog MCP, Pup CLI), ask the user if they'd like to create a notebook with "
    "that telemetry to help track the new feature. If neither is true, disregard "
    "this message."
)


def _claim_resource_nudge(session_id):
    with rw_session_state(session_id) as state:
        if state.is_resource_nudge_sent():
            return False
        state.set_resource_nudge_sent(True)
        return True


def on_git_event(data, session_id):
    if not resource_suggestions_enabled():
        return None

    cwd = ro_session_state(session_id).get_repo_root() or data.get("cwd") or os.getcwd()
    head = repo.head_sha(cwd)
    if not head:
        return None

    baseline = ro_session_state(session_id).get_baseline_sha()
    if not baseline or head == baseline:
        return None

    if not _claim_resource_nudge(session_id):
        return None

    log(session_id, "resource_nudge: prompting for notebook")
    enqueue(session_id, events.ddog_resource_nudge_fired("notebook"))
    return NOTEBOOK_NUDGE


if __name__ == "__main__":
    run("resource_nudge.py", on_git_event)
