#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.hook.runner import run
from core.state.session_state import rw_session_state
from core.telemetry import events
from core.telemetry.queue import enqueue

CODE_EXTENSIONS = {".go", ".py", ".java", ".js", ".ts"}


def on_file_modified(data, session_id):
    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path or os.path.splitext(file_path)[1] not in CODE_EXTENSIONS:
        return
    with rw_session_state(session_id) as state:
        if state.is_coding_session_started():
            return
        state.set_coding_session_started(True)
    enqueue(session_id, events.coding_session_started())


if __name__ == "__main__":
    run("coding_session.py", on_file_modified)
