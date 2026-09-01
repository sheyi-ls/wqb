import logging

from requests.auth import HTTPBasicAuth

from ..common.constants import LOCATION, POST
from .alpha import AlphaMixin
from .auth import AuthMixin
from .auto_auth_session import AutoAuthSession
from .catalog import CatalogMixin
from .simulation import SimulationMixin
from .spc import SpcMixin
from ..common.urls import URL_AUTHENTICATION

__all__ = ['WQBSession']


class WQBSession(
    AuthMixin,
    CatalogMixin,
    SimulationMixin,
    AlphaMixin,
    SpcMixin,
    AutoAuthSession,
):
    """HTTP implementation of :class:`wqb.api.BrainSession`."""

    def __init__(
        self,
        wqb_auth: tuple[str, str] | HTTPBasicAuth,
        *,
        logger: logging.Logger = logging.root,
        **kwargs,
    ) -> None:
        if not isinstance(wqb_auth, HTTPBasicAuth):
            wqb_auth = HTTPBasicAuth(*wqb_auth)
        kwargs['auth'] = wqb_auth
        super().__init__(
            POST,
            URL_AUTHENTICATION,
            auth_expected=lambda resp: 201 == resp.status_code,
            expected=lambda resp: resp.status_code not in (204, 401, 429),
            logger=logger,
            **kwargs,
        )
        self.expected_location = (
            lambda resp: self.expected(resp) and LOCATION in resp.headers
        )

    def __repr__(self) -> str:
        return f"<WQBSession [{repr(self.wqb_auth.username)}]>"
