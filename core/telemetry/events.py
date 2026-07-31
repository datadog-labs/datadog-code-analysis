# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import time


def _event(name, **metadata):
    return {"name": name, "metadata": metadata, "timestamp": int(time.time())}


def session_started(on_commit_telemetry_review_enabled, resource_suggestions_enabled):
    return _event(
        "session_started",
        on_commit_telemetry_review_enabled=on_commit_telemetry_review_enabled,
        resource_suggestions_enabled=resource_suggestions_enabled,
    )


def coding_session_started():
    return _event("coding_session_started")


def skills_listed():
    return _event("skills_listed")


def skill_loaded(skill_name):
    return _event("skill_loaded", skill_name=skill_name)


def edit_nudge_fired():
    return _event("edit_nudge_fired")


def ddog_resource_nudge_fired(resource_type):
    return _event("ddog_resource_nudge_fired", resource_type=resource_type)


def reviewer_ran(findings_count):
    return _event("reviewer_ran", findings_count=findings_count)


def agent_feedback_submitted(
    skill_name,
    skill_applies,
    telemetry_added=False,
    telemetry_removed=False,
    telemetry_adjusted=False,
):
    return _event(
        "agent_feedback_submitted",
        skill_name=skill_name,
        skill_applies=skill_applies,
        telemetry_added=telemetry_added,
        telemetry_removed=telemetry_removed,
        telemetry_adjusted=telemetry_adjusted,
    )


def agent_feedback_submitted_post_review(resolved):
    return _event("agent_feedback_submitted_post_review", resolved=resolved)
