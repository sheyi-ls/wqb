"""Simulation API."""
import asyncio
from collections.abc import Awaitable, Callable, Coroutine, Iterable
from typing import Any, Protocol

from requests import Response

from ..common.constants import Alpha, MultiAlpha

__all__ = ['SimulationAPI']


class SimulationAPI(Protocol):
    async def retry(
        self,
        method: str,
        url: str,
        *args,
        log: str | None = '',
        **kwargs,
    ) -> Coroutine[None, None, Response | None]: ...

    async def simulate(
        self,
        target: Alpha | MultiAlpha,
        *args,
        log: str | None = '',
        retry_log: str | None = None,
        **kwargs,
    ) -> Coroutine[None, None, Response | None]: ...

    async def multi_simulate(
        self,
        targets: MultiAlpha | Iterable[Alpha | str],
        *args,
        settings: dict[str, Any] | None = None,
        fetch_alpha_details: bool = False,
        log: str | None = '',
        retry_log: str | None = None,
        **kwargs,
    ) -> Coroutine[None, None, dict[str, Any] | None]: ...

    async def concurrent_simulate(
        self,
        targets: Iterable[Alpha | MultiAlpha],
        concurrency: int | asyncio.Semaphore,
        *args,
        return_exceptions: bool = False,
        log: str | None = '',
        log_gap: int = 100,
        **kwargs,
    ) -> Coroutine[None, None, list[Response | BaseException]]: ...
