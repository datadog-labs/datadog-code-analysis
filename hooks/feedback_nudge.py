#!/usr/bin/env python3
# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import SILENT_NUDGE_PREFIX
from core.env.config import get_plugin_root
from core.git import repo
from core.hook.runner import run
from core.logger.composite_logger import log
from core.state.session_state import ro_session_state, rw_session_state


def _format_skill_nudge(skills):
    plugin_root = get_plugin_root()
    names = ", ".join(skills)
    return (
        SILENT_NUDGE_PREFIX
        + "The user has opted into Datadog coding-time suggestions, and during this session that "
        f"led you to load these skill(s): {names}. Please report feedback on whether each one was useful. "
        "For each skill, judge whether its guidance applied anywhere in the feature or fix you "
        "worked on this session (against the whole task, not just the most recent change), then "
        "run exactly one of:\n"
        f"- `{plugin_root}/scripts/feedback.py skill <skill-name> not-applicable` if it didn't apply, e.g. "
        f"`{plugin_root}/scripts/feedback.py skill {skills[0]} not-applicable`\n"
        f"- `{plugin_root}/scripts/feedback.py skill <skill-name> applies --added=yes|no --removed=yes|no "
        "--adjusted=yes|no` if it did apply, e.g. "
        f"`{plugin_root}/scripts/feedback.py skill {skills[0]} applies --added=yes --removed=no --adjusted=no`, "
        "answering whether you added new telemetry (metrics/logs/traces), removed existing "
        "telemetry, and/or adjusted existing telemetry (e.g. naming, tags, log level -- not an "
        "add or a remove) as a result of the skill.\n"
        'Answer honestly -- "not-applicable"/"no" are expected outcomes when a skill didn\'t '
        "end up being relevant, not a failure."
    )


def _format_resolution_nudge(finding_count):
    plugin_root = get_plugin_root()
    return (
        SILENT_NUDGE_PREFIX
        + f"Earlier this session, a telemetry-guidance review flagged {finding_count} finding(s) "
        "on a prior commit, and you've now committed again. Please report whether you addressed "
        f"them: run `{plugin_root}/scripts/feedback.py review-resolution --resolved=all|some|none`, "
        f'e.g. `{plugin_root}/scripts/feedback.py review-resolution --resolved=some`. Use "all" if '
        'every finding was addressed, "some" if only part of them were, "none" if none were '
        '(including if you didn\'t revisit them). Answer honestly -- "none" is an expected '
        "outcome if the findings didn't seem worth acting on, not a failure."
    )


def _claim_feedback_nudge(session_id):
    with rw_session_state(session_id) as state:
        if state.is_feedback_prompted():
            return None
        loaded = state.get_loaded_skills()
        if not loaded:
            return None
        state.set_feedback_prompted(True)
        return loaded


def _claim_resolution_feedback(session_id, head):
    with rw_session_state(session_id) as state:
        if state.is_resolution_feedback_prompted():
            return None
        findings = state.get_review_findings()
        review_sha = state.get_review_sha()
        if not findings or not review_sha or review_sha == head:
            return None
        state.set_resolution_feedback_prompted(True)
        return list(findings)


def on_git_event(data, session_id):
    cwd = ro_session_state(session_id).get_repo_root() or data.get("cwd") or os.getcwd()
    head = repo.head_sha(cwd)
    if not head:
        return None

    messages = []

    baseline = ro_session_state(session_id).get_baseline_sha()
    if baseline and head != baseline:
        skills = _claim_feedback_nudge(session_id)
        if skills:
            log(session_id, f"feedback_nudge: prompting for skills={skills}")
            messages.append(_format_skill_nudge(skills))

    findings = _claim_resolution_feedback(session_id, head)
    if findings:
        log(session_id, f"feedback_nudge: prompting for review resolution, findings_count={len(findings)}")
        messages.append(_format_resolution_nudge(len(findings)))

    return "\n\n".join(messages) if messages else None


if __name__ == "__main__":
    run("feedback_nudge.py", on_git_event)
