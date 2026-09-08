#!/usr/bin/env python3
# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.credentials.composite_credential_resolver import get_dd_credentials
from core.logger.composite_logger import log
from core.telemetry import events
from core.telemetry.telemetry_event_client import TelemetryEventClient

RESOLVED_CHOICES = ("all", "some", "none")

IMPACT_PREVIEW_COUNTS = (
    ("--sessions-analyzed", "how many non-plugin sessions were analyzed"),
    ("--coding-sessions", "how many analyzed sessions actually changed code"),
    ("--not-applicable", "how many sessions no loaded guidance applied to"),
    ("--no-improvement-needed", "how many sessions already followed all relevant guidance"),
    ("--could-be-improved", "how many sessions had one or more opportunities"),
    ("--insufficient-evidence", "how many sessions lacked evidence to judge"),
    ("--add", "total add-telemetry opportunities across all sessions"),
    ("--adjust", "total adjust-telemetry opportunities across all sessions"),
    ("--remove", "total remove-or-avoid-telemetry opportunities across all sessions"),
)

IMPACT_REVIEW_COUNTS = (
    ("--sessions-analyzed", "how many plugin sessions were analyzed"),
    ("--coding-sessions", "how many analyzed sessions actually changed code"),
    ("--coding-sessions-with-guidance", "how many of those sessions also loaded guidance"),
    ("--coding-sessions-with-guidance-and-impact", "how many of those sessions had observed impact"),
    ("--sessions-with-tel-added", "how many impacted sessions added telemetry"),
    ("--sessions-with-tel-updated", "how many impacted sessions updated telemetry"),
    ("--sessions-with-tel-removed", "how many impacted sessions removed telemetry"),
    ("--positive", "impacted sessions with a positive net outcome"),
    ("--neutral", "impacted sessions with a neutral net outcome"),
    ("--negative", "impacted sessions with a negative net outcome"),
    ("--undetermined", "impacted sessions with an undetermined net outcome"),
)


def _count(value):
    try:
        count = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a non-negative integer") from None
    if count < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return count


def _yes_no(value):
    if value not in ("yes", "no"):
        raise argparse.ArgumentTypeError("must be 'yes' or 'no'")
    return value == "yes"


def _run_skill(session_id, args):
    safe_name = args.skill_name.replace("/", "__").replace(":", "__")
    applies = args.verdict == "applies"

    TelemetryEventClient(session_id, get_dd_credentials).send(
        [
            events.agent_feedback_submitted(
                skill_name=safe_name,
                skill_applies=applies,
                telemetry_added=args.added if applies else False,
                telemetry_removed=args.removed if applies else False,
                telemetry_adjusted=args.adjusted if applies else False,
            )
        ]
    )

    log(
        session_id,
        f"feedback.py: skill={args.skill_name} verdict={args.verdict}"
        + (f" added={args.added} removed={args.removed} adjusted={args.adjusted}" if applies else ""),
    )


def _run_impact_preview_results(session_id, args):
    TelemetryEventClient(session_id, get_dd_credentials).send(
        [
            events.impact_preview_submitted(
                sessions_analyzed=args.sessions_analyzed,
                coding_sessions=args.coding_sessions,
                not_applicable=args.not_applicable,
                no_improvement_needed=args.no_improvement_needed,
                could_be_improved=args.could_be_improved,
                insufficient_evidence=args.insufficient_evidence,
                opportunities_add=args.add,
                opportunities_adjust=args.adjust,
                opportunities_remove=args.remove,
            )
        ]
    )
    log(
        session_id,
        f"feedback.py: impact-preview-results sessions={args.sessions_analyzed} "
        f"coding_sessions={args.coding_sessions} "
        f"not_applicable={args.not_applicable} no_improvement_needed={args.no_improvement_needed} "
        f"could_be_improved={args.could_be_improved} insufficient_evidence={args.insufficient_evidence} "
        f"add={args.add} adjust={args.adjust} remove={args.remove}",
    )


def _run_impact_review_results(session_id, args):
    TelemetryEventClient(session_id, get_dd_credentials).send(
        [
            events.impact_review_submitted(
                sessions_analyzed=args.sessions_analyzed,
                coding_sessions=args.coding_sessions,
                coding_sessions_with_guidance=args.coding_sessions_with_guidance,
                coding_sessions_with_guidance_and_impact=args.coding_sessions_with_guidance_and_impact,
                sessions_with_tel_added=args.sessions_with_tel_added,
                sessions_with_tel_updated=args.sessions_with_tel_updated,
                sessions_with_tel_removed=args.sessions_with_tel_removed,
                positive_net_outcomes=args.positive,
                neutral_net_outcomes=args.neutral,
                negative_net_outcomes=args.negative,
                undetermined_net_outcomes=args.undetermined,
            )
        ]
    )
    log(
        session_id,
        f"feedback.py: impact-review-results sessions={args.sessions_analyzed} "
        f"coding_sessions={args.coding_sessions} "
        f"coding_sessions_with_guidance={args.coding_sessions_with_guidance} "
        f"coding_sessions_with_guidance_and_impact={args.coding_sessions_with_guidance_and_impact} "
        f"sessions_with_tel_added={args.sessions_with_tel_added} "
        f"sessions_with_tel_updated={args.sessions_with_tel_updated} "
        f"sessions_with_tel_removed={args.sessions_with_tel_removed} "
        f"positive={args.positive} neutral={args.neutral} negative={args.negative} "
        f"undetermined={args.undetermined}",
    )


def _run_review_resolution(session_id, args):
    TelemetryEventClient(session_id, get_dd_credentials).send(
        [events.agent_feedback_submitted_post_review(args.resolved)]
    )
    log(session_id, f"feedback.py: review-resolution resolved={args.resolved}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Report feedback to the Datadog code analysis plugin.")
    commands = parser.add_subparsers(dest="command", required=True)

    skill = commands.add_parser("skill", help="report feedback on a loaded telemetry skill")
    skill.add_argument("skill_name")
    verdicts = skill.add_subparsers(dest="verdict", required=True)
    verdicts.add_parser(
        "not-applicable",
        help="the skill's guidance didn't apply anywhere in this session's feature/fix",
    )
    applies = verdicts.add_parser(
        "applies",
        help="the skill's guidance applied somewhere in this session's feature/fix",
    )
    applies.add_argument(
        "--added",
        type=_yes_no,
        metavar="{yes,no}",
        required=True,
        help="did you add telemetry as a result of the skill",
    )
    applies.add_argument(
        "--removed",
        type=_yes_no,
        metavar="{yes,no}",
        required=True,
        help="did you remove telemetry as a result of the skill",
    )
    applies.add_argument(
        "--adjusted",
        type=_yes_no,
        metavar="{yes,no}",
        required=True,
        help="did you adjust existing telemetry (naming/tags/level, not add or remove) as a result of the skill",
    )

    review_resolution = commands.add_parser(
        "review-resolution",
        help="report whether you addressed the telemetry reviewer's prior findings on a later commit",
    )
    review_resolution.add_argument(
        "--resolved",
        choices=RESOLVED_CHOICES,
        required=True,
        help="did you address all, some, or none of the findings",
    )

    impact_preview = commands.add_parser(
        "impact-preview-results",
        help="report aggregate counts from an impact preview scan (counts only, no session content)",
    )
    for flag, description in IMPACT_PREVIEW_COUNTS:
        impact_preview.add_argument(flag, type=_count, metavar="N", required=True, help=description)

    impact_review = commands.add_parser(
        "impact-review-results",
        help="report aggregate counts from an impact review scan (counts only, no session content)",
    )
    for flag, description in IMPACT_REVIEW_COUNTS:
        impact_review.add_argument(flag, type=_count, metavar="N", required=True, help=description)

    args = parser.parse_args()

    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID", "unknown")

    if args.command == "skill":
        _run_skill(session_id, args)
    elif args.command == "impact-preview-results":
        _run_impact_preview_results(session_id, args)
    elif args.command == "impact-review-results":
        _run_impact_review_results(session_id, args)
    else:
        _run_review_resolution(session_id, args)
