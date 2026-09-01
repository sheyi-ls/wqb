"""Brain API GET with Retry-After polling and transient-error retry."""
from __future__ import annotations

import time
from typing import Any

from requests import Response

__all__ = ['wait_get']


def _retry_after_seconds(response: Response, *, default: float = 0.0) -> float:
    raw = response.headers.get('Retry-After', default)
    if raw in (None, '', '0', 0):
        return 0.0
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return default


def _has_body(response: Response) -> bool:
    return bool((response.text or '').strip())


def wait_get(
    session: Any,
    url: str,
    *args,
    max_retries: int = 10,
    default_retry_after: float = 5.0,
    retry_empty_body: bool = True,
    **kwargs,
) -> Response:
    """
    GET ``url`` respecting Brain ``Retry-After`` and retrying transient failures.

    Behaviour (aligned with ``kernel.session.wait_get`` + correlation empty-body
    handling used for ``recordsets/pnl`` / ``yearly-stats``):

    - Inner loop: honour ``Retry-After`` until zero.
    - ``429``: sleep ``Retry-After`` (or *default_retry_after*) and retry.
    - ``401``: call ``session.auth_request()`` when available, then retry.
    - ``200`` with empty body: sleep and retry (async recordset generation).
    - Outer loop: on other ``>= 400``, exponential backoff up to *max_retries*.

    Returns the final response (may still be 4xx/5xx or empty if retries
    exhausted). Callers should ``raise_for_status()`` / validate JSON as needed.
    """
    max_retries = max(1, max_retries)
    retries = 0
    response: Response | None = None

    while retries < max_retries:
        while True:
            response = session.get(url, *args, **kwargs)

            if response.status_code == 401 and callable(getattr(session, 'auth_request', None)):
                session.auth_request()
                continue

            if response.status_code == 429:
                time.sleep(_retry_after_seconds(response, default=default_retry_after))
                continue

            wait_s = _retry_after_seconds(response)
            if wait_s > 0:
                time.sleep(wait_s)
                continue

            if (
                retry_empty_body
                and response.status_code < 400
                and not _has_body(response)
            ):
                time.sleep(_retry_after_seconds(response, default=default_retry_after))
                continue

            break

        if response is not None and response.status_code < 400 and _has_body(response):
            return response

        time.sleep(min(2**retries, 60.0))
        retries += 1

    if response is not None:
        return response
    raise RuntimeError(f'wait_get received no response: {url}')
