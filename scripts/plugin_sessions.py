#!/usr/bin/env python3
# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import argparse
import datetime
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.state.session_state import session_state_file


DEFAULT_LIMIT = 20
PLUGIN_SESSION_START_NUDGE = "The user has opted into Datadog coding-time suggestions."


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a positive integer") from None
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def default_projects_dir() -> str:
    claude_config_dir = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(
        os.path.expanduser("~"), ".claude"
    )
    return os.path.join(os.path.expanduser(claude_config_dir), "projects")


def transcript_created_at(transcript_path: str) -> float | None:
    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as transcript:
            for line in transcript:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                timestamp = record.get("timestamp") if isinstance(record, dict) else None
                if not isinstance(timestamp, str):
                    continue
                try:
                    parsed = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                except ValueError:
                    continue
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=datetime.timezone.utc)
                return parsed.timestamp()
    except OSError:
        pass
    return None


def recent_transcripts(projects_dir: str, current_session_id: str | None) -> list[tuple[str, str]]:
    transcripts_by_session: dict[str, tuple[float, str]] = {}
    pattern = os.path.join(projects_dir, "*", "*.jsonl")
    for transcript_path in glob.iglob(pattern):
        if not os.path.isfile(transcript_path):
            continue
        session_id = os.path.splitext(os.path.basename(transcript_path))[0]
        if session_id == current_session_id:
            continue

        created_at = transcript_created_at(transcript_path)
        if created_at is None:
            continue

        existing = transcripts_by_session.get(session_id)
        if existing is None or (created_at, transcript_path) > existing:
            transcripts_by_session[session_id] = (created_at, transcript_path)

    newest_first = sorted(
        transcripts_by_session.items(), key=lambda item: (item[1][0], item[0]), reverse=True
    )
    return [(session_id, transcript_path) for session_id, (_, transcript_path) in newest_first]


def list_for_review(
    limit: int,
    projects_dir: str | None = None,
    state_dir: str | None = None,
    current_session_id: str | None = None,
) -> dict[str, list[dict[str, str]]]:
    projects_dir = projects_dir or default_projects_dir()
    state_dir = state_dir or os.path.join(os.path.expanduser("~"), ".dd-code-analysis", "state")

    candidates = []
    for session_id, transcript_path in recent_transcripts(projects_dir, current_session_id):
        state_path = session_state_file(session_id, state_dir)
        if not os.path.isfile(state_path):
            continue
        candidates.append(
            {
                "session_id": session_id,
                "transcript_path": os.path.abspath(transcript_path),
                "state_path": os.path.abspath(state_path),
            }
        )
        if len(candidates) == limit:
            break
    return {"candidates": candidates}


def has_plugin_session_start_nudge(transcript_path: str) -> bool | None:
    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as transcript:
            return any(PLUGIN_SESSION_START_NUDGE in line for line in transcript)
    except OSError:
        return None


def list_for_preview(
    limit: int,
    projects_dir: str | None = None,
    current_session_id: str | None = None,
) -> dict[str, list[dict[str, str]]]:
    projects_dir = projects_dir or default_projects_dir()

    candidates = []
    for session_id, transcript_path in recent_transcripts(projects_dir, current_session_id):
        has_nudge = has_plugin_session_start_nudge(transcript_path)
        if has_nudge is False:
            candidates.append(
                {
                    "session_id": session_id,
                    "transcript_path": os.path.abspath(transcript_path),
                }
            )
            if len(candidates) == limit:
                break
    return {"candidates": candidates}


def main() -> None:
    parser = argparse.ArgumentParser(description="Find Claude sessions for plugin impact analysis.")
    commands = parser.add_subparsers(dest="command", required=True)
    review_command = commands.add_parser(
        "list-for-review",
        help="list recent sessions that have both a Claude transcript and Datadog plugin state",
    )
    review_command.add_argument("--limit", type=positive_int, default=DEFAULT_LIMIT)
    preview_command = commands.add_parser(
        "list-for-preview",
        help="list recent sessions without the Datadog plugin session-start nudge",
    )
    preview_command.add_argument("--limit", type=positive_int, default=DEFAULT_LIMIT)
    args = parser.parse_args()

    if args.command == "list-for-review":
        result = list_for_review(
            limit=args.limit,
            current_session_id=os.environ.get("CLAUDE_CODE_SESSION_ID"),
        )
    else:
        result = list_for_preview(
            limit=args.limit,
            current_session_id=os.environ.get("CLAUDE_CODE_SESSION_ID"),
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
