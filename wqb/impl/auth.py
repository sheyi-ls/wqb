"""Authentication API mixin for WQBSession."""
from requests import Response
from requests.auth import HTTPBasicAuth

from ..common.urls import URL_AUTHENTICATION

__all__ = ['AuthMixin']


class AuthMixin:
    @property
    def wqb_auth(
        self,
    ) -> HTTPBasicAuth:
        """
        `wqb_auth`
        """
        return self.kwargs['auth']

    @wqb_auth.setter
    def wqb_auth(
        self,
        wqb_auth: tuple[str, str] | HTTPBasicAuth,
    ) -> None:
        """
        `wqb_auth`
        """
        if not isinstance(wqb_auth, HTTPBasicAuth):
            wqb_auth = HTTPBasicAuth(*wqb_auth)
        self.kwargs['auth'] = wqb_auth

    def get_authentication(
        self,
        *args,
        log: str | None = '',
        **kwargs,
    ) -> Response:
        """
        Sends a GET request to `URL_AUTHENTICATION`.

        Parameters
        ----------
        log: str | None = ''
            The message to be appended. If *None*, logging is disabled.

        Returns
        -------
        Response
            A `Response` object.

        Notes
        -----
        `args` and `kwargs` are passed to `Session.get`.

        Examples
        --------
        >>> wqbs = wqb.WQBSession(('<email>', '<password>'))
        >>> resp = wqbs.get_authentication()
        >>> resp.ok
        True
        """
        url = URL_AUTHENTICATION
        resp = self.get(url, *args, **kwargs)
        if log is not None:
            self.logger.info(
                '\n'.join(
                    (
                        f"{self}.get_authentication(...) [",
                        f"    {url}",
                        f"]: {log}",
                    )
                )
            )
        return resp

    def post_authentication(
        self,
        *args,
        log: str | None = '',
        **kwargs,
    ) -> Response:
        """
        Sends a POST request to `URL_AUTHENTICATION`.

        Parameters
        ----------
        log: str | None = ''
            The message to be appended. If *None*, logging is disabled.

        Returns
        -------
        Response
            A `Response` object.

        Notes
        -----
        `args` and `kwargs` are passed to `Session.post`.

        Examples
        --------
        >>> wqbs = wqb.WQBSession(('<email>', '<password>'))
        >>> resp = wqbs.post_authentication(auth=wqbs.wqb_auth)
        >>> resp.ok
        True
        """
        url = URL_AUTHENTICATION
        resp = self.post(url, *args, auth=self.wqb_auth, **kwargs)
        if log is not None:
            self.logger.info(
                '\n'.join(
                    (
                        f"{self}.post_authentication(...) [",
                        f"    {url}",
                        f"]: {log}",
                    )
                )
            )
        return resp

    def delete_authentication(
        self,
        *args,
        log: str | None = '',
        **kwargs,
    ) -> Response:
        """
        Sends a DELETE request to `URL_AUTHENTICATION`.

        Parameters
        ----------
        log: str | None = ''
            The message to be appended. If *None*, logging is disabled.

        Returns
        -------
        Response
            A `Response` object.

        Notes
        -----
        `args` and `kwargs` are passed to `Session.delete`.

        Examples
        --------
        >>> wqbs = wqb.WQBSession(('<email>', '<password>'))
        >>> resp = wqbs.delete_authentication()
        >>> resp.ok
        True
        """
        url = URL_AUTHENTICATION
        resp = self.delete(url, *args, **kwargs)
        if log is not None:
            self.logger.info(
                '\n'.join(
                    (
                        f"{self}.delete_authentication(...) [",
                        f"    {url}",
                        f"]: {log}",
                    )
                )
            )
        return resp

    def head_authentication(
        self,
        *args,
        log: str | None = '',
        **kwargs,
    ) -> Response:
        """
        Sends a HEAD request to `URL_AUTHENTICATION`.

        Parameters
        ----------
        log: str | None = ''
            The message to be appended. If *None*, logging is disabled.

        Returns
        -------
        Response
            A `Response` object.

        Notes
        -----
        `args` and `kwargs` are passed to `Session.head`.

        Examples
        --------
        >>> wqbs = wqb.WQBSession(('<email>', '<password>'))
        >>> resp = wqbs.head_authentication()
        >>> resp.ok
        True
        """
        url = URL_AUTHENTICATION
        resp = self.head(url, *args, **kwargs)
        if log is not None:
            self.logger.info(
                '\n'.join(
                    (
                        f"{self}.head_authentication(...) [",
                        f"    {url}",
                        f"]: {log}",
                    )
                )
            )
        return resp
