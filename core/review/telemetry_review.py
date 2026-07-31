import contextlib
import os
import tempfile

from core.credentials.composite_credential_resolver import get_dd_credentials
from core.llm.claude_client import LLMError, call_claude
from core.logger.composite_logger import log
from core.skills.skill_client import SkillClient
from core.telemetry import events
from core.telemetry.queue import enqueue

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file": {"type": "string"},
                    "category": {
                        "type": "string",
                        "description": "short slug for the guidance this relates to, e.g. missing_metric, missing_log, missing_trace_span",
                    },
                    "description": {
                        "type": "string",
                        "description": "one or two sentences: what's missing, and where",
                    },
                },
                "required": ["file", "category", "description"],
            },
        },
    },
    "required": ["findings"],
}

REVIEW_SYSTEM_PROMPT = (
    "You review a git diff against a set of coding-telemetry best practices "
    "(logging, metrics, tracing). Only report a finding when the guidance "
    "clearly applies to code actually changed in the diff -- do not invent "
    "issues, do not comment on style or correctness, and do not flag "
    "anything outside the telemetry guidance provided. If nothing in the "
    "diff warrants a finding, return an empty findings list."
)


@contextlib.contextmanager
def _temp_diff_file(diff, session_id):
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".diff", prefix=f"dd-code-analysis-plugin-{session_id}-review-", delete=False
    ) as f:
        f.write(diff)
        path = f.name
    try:
        yield path
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def run(session_id, cwd, diff):
    guidance = SkillClient(session_id, get_dd_credentials).load_guidance()
    if not guidance:
        log(session_id, "review skipped, no guidance available")
        return None

    findings: list = []
    try:
        with _temp_diff_file(diff, session_id) as diff_path:
            result = call_claude(
                REVIEW_SYSTEM_PROMPT,
                f"Guidance:\n{guidance}\n\n"
                f"The diff to review is at {diff_path} -- Read it (paging with "
                "offset/limit if it's large) before answering.",
                REVIEW_SCHEMA,
                cwd=cwd,
                extra_dirs=[os.path.dirname(diff_path)],
            )
        findings = result.get("findings", []) or []
    except LLMError as e:
        log(session_id, f"review call failed: {e}")

    log(
        session_id,
        f"review ran, diff_chars={len(diff)}, findings_count={len(findings)}, "
        f"categories={[f.get('category') for f in findings]}",
    )
    enqueue(session_id, events.reviewer_ran(len(findings)))
    return findings


def format_findings_message(findings):
    lines = ["Telemetry-guidance review found the following:"]
    for f in findings:
        lines.append(f"- [{f.get('category', 'finding')}] {f.get('file', '?')}: {f.get('description', '')}")
    lines.append(
        "These are suggestions, not requirements. Present them to the user and let "
        "them decide whether any are worth addressing -- do not implement fixes for "
        "them without the user's go-ahead."
    )
    return "\n".join(lines)
