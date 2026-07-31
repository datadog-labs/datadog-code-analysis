# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

from core.credentials.obfuscated_credential_cache import ObfuscatedCredentialCache
from core.credentials.types import CredentialResolver
from core.credentials.user_config_credential_resolver import UserConfigCredentialResolver

CACHE_FILENAME = "user-config-creds.json"


class CachedUserConfigCredentialResolver(CredentialResolver):
    def __init__(self):
        self._cache = ObfuscatedCredentialCache(CACHE_FILENAME)

    def resolve_api_app_key(self, session_id):
        return self._cache.read()


def configure_user_cfg_cred_cache(session_id):
    cred = UserConfigCredentialResolver().resolve_api_app_key(session_id)
    cache = ObfuscatedCredentialCache(CACHE_FILENAME)
    if cred:
        cache.write(cred)
    else:
        cache.clear()
