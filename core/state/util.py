import os
import random
import time

from core.logger.composite_logger import log
from core.state.session_state import ReadOnlySessionState

STATE_MAX_AGE_SECONDS = 30 * 24 * 60 * 60
STATE_CLEANUP_CHANCE = 0.1


def cleanup_old_state(session_id=None):
    if random.random() >= STATE_CLEANUP_CHANCE:
        return
    try:
        state_dir = ReadOnlySessionState._state_dir()
        cutoff = time.time() - STATE_MAX_AGE_SECONDS
        for name in os.listdir(state_dir):
            path = os.path.join(state_dir, name)
            try:
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
            except OSError:
                pass
    except Exception as e:
        log(session_id or "unknown", f"cleanup_old_state failed: {e}")
