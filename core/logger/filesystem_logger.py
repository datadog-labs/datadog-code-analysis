import datetime
import os
import tempfile

from core.logger.types import Logger


class FilesystemLogger(Logger):
    def log(self, session_id, msg):
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            path = os.path.join(tempfile.gettempdir(), f"dd-code-analysis-plugin-{session_id}.log")
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            with os.fdopen(fd, "a") as f:
                os.chmod(path, 0o600)
                f.write(f"[{ts}] {msg}\n")
        except Exception:
            pass
