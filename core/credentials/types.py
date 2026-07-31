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
