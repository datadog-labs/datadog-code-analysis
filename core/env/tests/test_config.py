# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import os
import unittest
from unittest.mock import patch

from core.env.config import get_plugin_root, get_plugin_version


class GetPluginRootTest(unittest.TestCase):
    def test_env_var_wins(self):
        with patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": "/somewhere/else/"}):
            self.assertEqual(get_plugin_root(), "/somewhere/else")

    def test_fallback_finds_the_directory_holding_the_manifest(self):
        env = dict(os.environ)
        env.pop("CLAUDE_PLUGIN_ROOT", None)
        with patch.dict(os.environ, env, clear=True):
            root = get_plugin_root()
        self.assertTrue(
            os.path.isfile(os.path.join(root, ".claude-plugin", "plugin.json")),
            f"{root} is not the plugin root -- the __file__ fallback breaks when config.py moves",
        )


class GetPluginVersionTest(unittest.TestCase):
    def test_reads_the_manifest_version(self):
        env = dict(os.environ)
        env.pop("CLAUDE_PLUGIN_ROOT", None)
        with patch.dict(os.environ, env, clear=True):
            self.assertNotEqual(get_plugin_version(), "unknown")

    def test_unknown_when_the_manifest_is_missing(self):
        with patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": "/nonexistent"}):
            self.assertEqual(get_plugin_version(), "unknown")
