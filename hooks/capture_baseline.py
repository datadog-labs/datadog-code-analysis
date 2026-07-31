#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.git import repo
from core.hook.runner import run
from core.logger.composite_logger import log
from core.state.session_state import ro_session_state, rw_session_state


def on_file_modified(data, session_id):
    file_path = data.get("tool_input", {}).get("file_path")
    if not file_path:
        return
    if ro_session_state(session_id).get_repo_root():
        return

    cwd = os.path.dirname(file_path)
    resolved, error = repo.resolve(cwd)
    if not resolved:
        log(session_id, f"capture_baseline: could not resolve repo at cwd={cwd}: {error}")
        return

    root, sha = resolved
    with rw_session_state(session_id) as state:
        if state.get_repo_root():
            return
        state.set_repo_root(root)
        state.set_baseline_sha(sha)

    log(session_id, f"capture_baseline: repo_root={root}, baseline_sha={sha}")


if __name__ == "__main__":
    run("capture_baseline.py", on_file_modified)
