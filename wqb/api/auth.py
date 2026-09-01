"""Authentication API."""
from typing import Protocol

from requests import Response
from requests.auth import HTTPBasicAuth

__all__ = ['AuthAPI']


class AuthAPI(Protocol):
    @property
    def wqb_auth(self) -> HTTPBasicAuth: ...

    def get_authentication(self, *args, log: str | None = '', **kwargs) -> Response: ...

    def post_authentication(self, *args, log: str | None = '', **kwargs) -> Response: ...

    def delete_authentication(self, *args, log: str | None = '', **kwargs) -> Response: ...

    def head_authentication(self, *args, log: str | None = '', **kwargs) -> Response: ...
