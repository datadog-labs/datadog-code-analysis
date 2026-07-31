#!/usr/bin/env python3
# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.env.config import on_commit_telemetry_review_enabled
from core.git import repo
from core.hook.runner import run
from core.logger.composite_logger import log
from core.review import telemetry_review
from core.state.session_state import ro_session_state, rw_session_state
from core.telemetry.queue import drain

DIFF_EXCLUDE_PATHSPECS = [":(exclude,glob)*.pb.go", ":(exclude,glob)**/*.pb.go"]


def claim_review(state, cwd, head):
    if state.is_review_done():
        return None

    baseline = state.get_baseline_sha() or head
    diff = repo.diff(cwd, baseline, head, DIFF_EXCLUDE_PATHSPECS)
    if not diff.strip():
        return None
    state.set_review_done(True)
    state.set_review_sha(head)
    return diff


def on_git_event(data, session_id):
    cwd = ro_session_state(session_id).get_repo_root()
    if not cwd:
        log(session_id, "reviewer: skipped, no repo locked in yet")
        return None

    head = repo.head_sha(cwd)
    if not head:
        log(session_id, "reviewer: skipped, could not resolve HEAD sha")
        return None

    with rw_session_state(session_id) as state:
        diff = claim_review(state, cwd, head)
    if diff is None:
        return None

    log(session_id, f"reviewer: review claimed at head={head}")
    findings = telemetry_review.run(session_id, cwd, diff)
    if not findings:
        return None

    with rw_session_state(session_id) as state:
        state.set_review_findings(findings)
    return telemetry_review.format_findings_message(findings)


def _review_and_drain(data, session_id):
    message = on_git_event(data, session_id)
    drain(session_id)
    return message


if __name__ == "__main__":
    if not on_commit_telemetry_review_enabled():
        sys.exit(0)
    run("reviewer.py", _review_and_drain, rewake=True)
