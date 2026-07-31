# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import unittest
from unittest.mock import MagicMock

from core.logger import composite_logger
from core.logger.composite_logger import CompositeLogger


class CompositeLoggerTest(unittest.TestCase):
    def test_logs_to_every_logger(self):
        first = MagicMock()
        second = MagicMock()
        logger = CompositeLogger([first, second])

        logger.log("sid", "hello")

        first.log.assert_called_once_with("sid", "hello")
        second.log.assert_called_once_with("sid", "hello")


class LogTest(unittest.TestCase):
    def setUp(self):
        self.original_logger = composite_logger._logger

    def tearDown(self):
        composite_logger._logger = self.original_logger

    def test_log_delegates_to_active_logger(self):
        composite_logger._logger = MagicMock()

        composite_logger.log("sid", "hello")

        composite_logger._logger.log.assert_called_once_with("sid", "hello")
