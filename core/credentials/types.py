# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import abc
from dataclasses import dataclass


@dataclass(frozen=True)
class APIAppKeyCredential:
    api_key: str
    app_key: str
    dd_site: str


class CredentialResolver(abc.ABC):
    @abc.abstractmethod
    def resolve_api_app_key(self, session_id):
        pass
