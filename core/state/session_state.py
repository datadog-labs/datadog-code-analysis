# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import contextlib
import json
import os

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None  # type: ignore[assignment]

from core.env.paths import app_home


def session_file(session_id, suffix):
    return ReadOnlySessionState._state_path(session_id) + suffix


class ReadOnlySessionState:
    def __init__(self, data):
        self._data = data

    @classmethod
    def _state_dir(cls):
        return os.path.join(app_home(), "state")

    @classmethod
    def _state_path(cls, session_id):
        return os.path.join(cls._state_dir(), f"{session_id}.json")

    @classmethod
    def _read_data(cls, session_id):
        try:
            with open(cls._state_path(session_id)) as f:
                return json.load(f)
        except Exception:
            return {}

    @classmethod
    def _open(cls, session_id):
        return cls(cls._read_data(session_id))

    def is_skills_listed(self):
        return bool(self._data.get("skills_listed"))

    def is_edit_nudge_sent(self):
        return bool(self._data.get("edit_nudge_sent"))

    def is_coding_session_started(self):
        return bool(self._data.get("coding_session_started"))

    def is_resource_nudge_sent(self):
        return bool(self._data.get("resource_nudge_sent"))

    def is_feedback_prompted(self):
        return bool(self._data.get("feedback_prompted"))

    def is_resolution_feedback_prompted(self):
        return bool(self._data.get("resolution_feedback_prompted"))

    def is_review_done(self):
        return bool(self._data.get("review_done"))

    def get_repo_root(self):
        return self._data.get("repo_root")

    def get_baseline_sha(self):
        return self._data.get("baseline_sha")

    def get_review_sha(self):
        return self._data.get("review_sha")

    def get_loaded_skills(self):
        return list(self._data.get("loaded_skills") or [])

    def get_review_findings(self):
        return self._data.get("review_findings")

    def get_pending_events(self):
        return list(self._data.get("pending_events") or [])


class ReadWriteSessionState(ReadOnlySessionState):
    @staticmethod
    def _atomic_write_json(path, data):
        tmp_path = f"{path}.{os.getpid()}.tmp"
        with open(tmp_path, "w") as f:
            json.dump(data, f)
        os.replace(tmp_path, path)

    @classmethod
    @contextlib.contextmanager
    def _open(cls, session_id):
        path = cls._state_path(session_id)
        try:
            os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
        except OSError:
            pass

        lock_file = open(f"{path}.lock", "w") if fcntl is not None else None
        try:
            if lock_file is not None:
                fcntl.flock(lock_file, fcntl.LOCK_EX)
            data = cls._read_data(session_id)
            yield cls(data)
            cls._atomic_write_json(path, data)
        finally:
            if lock_file is not None:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
                lock_file.close()

    def set_skills_listed(self, value):
        self._data["skills_listed"] = value

    def set_edit_nudge_sent(self, value):
        self._data["edit_nudge_sent"] = value

    def set_coding_session_started(self, value):
        self._data["coding_session_started"] = value

    def set_resource_nudge_sent(self, value):
        self._data["resource_nudge_sent"] = value

    def set_feedback_prompted(self, value):
        self._data["feedback_prompted"] = value

    def set_resolution_feedback_prompted(self, value):
        self._data["resolution_feedback_prompted"] = value

    def set_review_done(self, value):
        self._data["review_done"] = value

    def set_repo_root(self, value):
        self._data["repo_root"] = value

    def set_baseline_sha(self, value):
        self._data["baseline_sha"] = value

    def set_review_sha(self, value):
        self._data["review_sha"] = value

    def set_review_findings(self, value):
        self._data["review_findings"] = value

    def add_loaded_skill(self, name):
        loaded = self._data.get("loaded_skills") or []
        if name not in loaded:
            loaded.append(name)
        self._data["loaded_skills"] = loaded

    def append_pending_event(self, event):
        pending = self._data.get("pending_events") or []
        pending.append(event)
        self._data["pending_events"] = pending

    def drop_pending_events(self, count):
        pending = self._data.get("pending_events") or []
        self._data["pending_events"] = pending[count:]


def ro_session_state(session_id):
    return ReadOnlySessionState._open(session_id)


def rw_session_state(session_id):
    return ReadWriteSessionState._open(session_id)
