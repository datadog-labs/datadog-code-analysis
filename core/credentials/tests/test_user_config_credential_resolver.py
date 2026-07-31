# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import os
import unittest
from unittest.mock import patch

from core.credentials.user_config_credential_resolver import UserConfigCredentialResolver

OPTION_KEYS = (
    "CLAUDE_PLUGIN_OPTION_DD_SITE",
    "CLAUDE_PLUGIN_OPTION_DD_API_KEY",
    "CLAUDE_PLUGIN_OPTION_DD_APP_KEY",
)


class UserConfigCredentialResolverTest(unittest.TestCase):
    def setUp(self):
        self.resolver = UserConfigCredentialResolver()
        self.env_patch = patch.dict("os.environ", {}, clear=False)
        self.env_patch.start()
        for key in OPTION_KEYS:
            os.environ.pop(key, None)

    def tearDown(self):
        self.env_patch.stop()

    def test_returns_none_when_nothing_set(self):
        self.assertIsNone(self.resolver.resolve_api_app_key("sid"))

    def test_returns_credential_when_all_set(self):
        with patch.dict(
            "os.environ",
            {
                "CLAUDE_PLUGIN_OPTION_DD_SITE": "datadoghq.eu",
                "CLAUDE_PLUGIN_OPTION_DD_API_KEY": "abc",
                "CLAUDE_PLUGIN_OPTION_DD_APP_KEY": "def",
            },
        ):
            cred = self.resolver.resolve_api_app_key("sid")
        self.assertEqual(cred.dd_site, "datadoghq.eu")
        self.assertEqual(cred.api_key, "abc")
        self.assertEqual(cred.app_key, "def")

    def test_returns_none_when_dd_site_missing(self):
        with patch.dict(
            "os.environ",
            {
                "CLAUDE_PLUGIN_OPTION_DD_API_KEY": "abc",
                "CLAUDE_PLUGIN_OPTION_DD_APP_KEY": "def",
            },
        ):
            self.assertIsNone(self.resolver.resolve_api_app_key("sid"))

    def test_returns_none_when_api_key_empty(self):
        with patch.dict(
            "os.environ",
            {
                "CLAUDE_PLUGIN_OPTION_DD_SITE": "datadoghq.eu",
                "CLAUDE_PLUGIN_OPTION_DD_API_KEY": "",
                "CLAUDE_PLUGIN_OPTION_DD_APP_KEY": "def",
            },
        ):
            self.assertIsNone(self.resolver.resolve_api_app_key("sid"))

    def test_returns_none_when_app_key_missing(self):
        with patch.dict(
            "os.environ",
            {
                "CLAUDE_PLUGIN_OPTION_DD_SITE": "datadoghq.eu",
                "CLAUDE_PLUGIN_OPTION_DD_API_KEY": "abc",
            },
        ):
            self.assertIsNone(self.resolver.resolve_api_app_key("sid"))
