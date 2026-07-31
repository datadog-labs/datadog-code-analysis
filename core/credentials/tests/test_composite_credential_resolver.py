import unittest
from unittest.mock import MagicMock

from core.credentials.composite_credential_resolver import CompositeCredentialResolver


class CompositeCredentialResolverTest(unittest.TestCase):
    def test_returns_first_successful_resolver(self):
        first = MagicMock()
        first.resolve_api_app_key.return_value = "cred-from-first"
        second = MagicMock()
        resolver = CompositeCredentialResolver([first, second])

        self.assertEqual(resolver.resolve_api_app_key("sid"), "cred-from-first")
        second.resolve_api_app_key.assert_not_called()

    def test_falls_through_to_next_resolver(self):
        first = MagicMock()
        first.resolve_api_app_key.return_value = None
        second = MagicMock()
        second.resolve_api_app_key.return_value = "cred-from-second"
        resolver = CompositeCredentialResolver([first, second])

        self.assertEqual(resolver.resolve_api_app_key("sid"), "cred-from-second")

    def test_returns_none_when_all_fail(self):
        first = MagicMock()
        first.resolve_api_app_key.return_value = None
        second = MagicMock()
        second.resolve_api_app_key.return_value = None
        resolver = CompositeCredentialResolver([first, second])

        self.assertIsNone(resolver.resolve_api_app_key("sid"))
