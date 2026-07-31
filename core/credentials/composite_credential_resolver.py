from core.credentials.cached_user_config_credential_resolver import CachedUserConfigCredentialResolver
from core.credentials.types import CredentialResolver
from core.credentials.user_config_credential_resolver import UserConfigCredentialResolver
from core.logger.composite_logger import log


class CompositeCredentialResolver(CredentialResolver):
    def __init__(self, resolvers):
        self._resolvers = resolvers

    def resolve_api_app_key(self, session_id):
        for resolver in self._resolvers:
            cred = resolver.resolve_api_app_key(session_id)
            if cred:
                return cred
        log(session_id, "failed to resolve credentials from any source")
        return None


_default_resolver = CompositeCredentialResolver(
    [
        UserConfigCredentialResolver(),
        CachedUserConfigCredentialResolver(),
    ]
)


def get_dd_credentials(session_id):
    return _default_resolver.resolve_api_app_key(session_id)
