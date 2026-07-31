# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

from core.logger.filesystem_logger import FilesystemLogger
from core.logger.types import Logger


class CompositeLogger(Logger):
    def __init__(self, loggers):
        self._loggers = loggers

    def log(self, session_id, msg):
        for logger in self._loggers:
            logger.log(session_id, msg)


_logger: Logger = CompositeLogger([FilesystemLogger()])


def log(session_id, msg):
    _logger.log(session_id, msg)
