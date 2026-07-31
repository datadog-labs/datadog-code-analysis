# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import os

from core.credentials.types import APIAppKeyCredential, CredentialResolver


class UserConfigCredentialResolver(CredentialResolver):
    def resolve_api_app_key(self, session_id):
        dd_site = os.environ.get("CLAUDE_PLUGIN_OPTION_DD_SITE")
        api_key = os.environ.get("CLAUDE_PLUGIN_OPTION_DD_API_KEY")
        app_key = os.environ.get("CLAUDE_PLUGIN_OPTION_DD_APP_KEY")
        if not (dd_site and api_key and app_key):
            return None
        return APIAppKeyCredential(api_key=api_key, app_key=app_key, dd_site=dd_site)
