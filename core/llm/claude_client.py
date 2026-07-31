# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import json
import shutil
import subprocess

_DEFAULT_MODEL = "haiku"
_READ_ONLY_TOOLS = "Read,Grep,Glob"


class LLMError(Exception):
    pass


def _claude_bin():
    path = shutil.which("claude")
    if not path:
        raise LLMError("claude CLI not found on PATH")
    return path


def call_claude(system, user_prompt, json_schema, model=None, timeout=550, cwd=None, extra_dirs=None):
    cmd = [
        _claude_bin(),
        "-p",
        "--output-format",
        "json",
        "--model",
        model or _DEFAULT_MODEL,
        "--no-session-persistence",
        "--safe-mode",
        "--json-schema",
        json.dumps(json_schema),
        "--system-prompt",
        system,
    ]
    if cwd:
        cmd += [
            "--tools",
            _READ_ONLY_TOOLS,
            "--allowedTools",
            _READ_ONLY_TOOLS.replace(",", " "),
            "--add-dir",
            cwd,
            *(extra_dirs or []),
        ]
    else:
        cmd += ["--tools", ""]
    cmd += ["--", user_prompt]

    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout, cwd=cwd)
    except subprocess.TimeoutExpired as e:
        raise LLMError(f"claude -p timed out after {timeout}s") from e
    except Exception as e:
        raise LLMError(f"failed to run claude -p: {e}") from e

    if proc.returncode != 0:
        raise LLMError(f"claude -p exited {proc.returncode}: {proc.stderr.decode(errors='replace')}")

    try:
        parsed = json.loads(proc.stdout.decode(errors="replace"))
    except json.JSONDecodeError as e:
        raise LLMError(f"claude -p returned non-JSON stdout: {e}") from e

    if parsed.get("is_error"):
        raise LLMError(f"claude -p reported an error: {parsed}")

    structured = parsed.get("structured_output")
    if structured is None:
        raise LLMError(f"claude -p response had no structured_output: {parsed}")
    return structured
