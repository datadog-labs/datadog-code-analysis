# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import time
from enum import Enum


class Purpose(str, Enum):
    CODING_SESSION = "coding-session"
    PLUGIN_PREVIEW = "plugin-preview"

    def __str__(self):
        return self.value


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


def skills_listed(purpose=Purpose.CODING_SESSION):
    return _event("skills_listed", purpose=purpose.value)


def skill_loaded(skill_name, purpose=Purpose.CODING_SESSION):
    return _event("skill_loaded", skill_name=skill_name, purpose=purpose.value)


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


def impact_preview_submitted(
    sessions_analyzed,
    coding_sessions,
    not_applicable,
    no_improvement_needed,
    could_be_improved,
    insufficient_evidence,
    opportunities_add,
    opportunities_adjust,
    opportunities_remove,
):
    return _event(
        "impact_preview_submitted",
        sessions_analyzed=sessions_analyzed,
        coding_sessions=coding_sessions,
        not_applicable=not_applicable,
        no_improvement_needed=no_improvement_needed,
        could_be_improved=could_be_improved,
        insufficient_evidence=insufficient_evidence,
        opportunities_add=opportunities_add,
        opportunities_adjust=opportunities_adjust,
        opportunities_remove=opportunities_remove,
    )


def impact_review_submitted(
    sessions_analyzed,
    coding_sessions,
    coding_sessions_with_guidance,
    coding_sessions_with_guidance_and_impact,
    sessions_with_tel_added,
    sessions_with_tel_updated,
    sessions_with_tel_removed,
    positive_net_outcomes,
    neutral_net_outcomes,
    negative_net_outcomes,
    undetermined_net_outcomes,
):
    return _event(
        "impact_review_submitted",
        sessions_analyzed=sessions_analyzed,
        coding_sessions=coding_sessions,
        coding_sessions_with_guidance=coding_sessions_with_guidance,
        coding_sessions_with_guidance_and_impact=coding_sessions_with_guidance_and_impact,
        sessions_with_tel_added=sessions_with_tel_added,
        sessions_with_tel_updated=sessions_with_tel_updated,
        sessions_with_tel_removed=sessions_with_tel_removed,
        positive_net_outcomes=positive_net_outcomes,
        neutral_net_outcomes=neutral_net_outcomes,
        negative_net_outcomes=negative_net_outcomes,
        undetermined_net_outcomes=undetermined_net_outcomes,
    )
