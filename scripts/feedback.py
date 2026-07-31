#!/usr/bin/env python3
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.credentials.composite_credential_resolver import get_dd_credentials
from core.logger.composite_logger import log
from core.telemetry import events
from core.telemetry.telemetry_event_client import TelemetryEventClient

RESOLVED_CHOICES = ("all", "some", "none")


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

    args = parser.parse_args()

    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID", "unknown")

    if args.command == "skill":
        _run_skill(session_id, args)
    else:
        _run_review_resolution(session_id, args)
