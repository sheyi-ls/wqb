"""Alpha API."""
from collections.abc import Generator, Iterable
from pathlib import Path
from typing import Any, Protocol

from requests import Response

from ..common.constants import (
    Null,
    Region,
    Delay,
    Universe,
    InstrumentType,
    Status,
    AlphaType,
    AlphaCategory,
    Language,
    Color,
    Neutralization,
    UnitHandling,
    NanHandling,
    Pasteurization,
    AlphasOrder,
)
from ..common.filter_range import FilterRange

__all__ = ['AlphaAPI']


class AlphaAPI(Protocol):
    def locate_alpha(self, alpha_id: str, *args, log: str | None = '', **kwargs) -> Response: ...

    def locate_alpha_brief(
        self, alpha_id: str, *args, log: str | None = '', **kwargs
    ) -> dict[str, Any]: ...

    def get_pnl(
        self, alpha_id: str, *args, max_retries: int = 10, log: str | None = '', **kwargs
    ) -> Response: ...

    def get_yearly_stats(
        self, alpha_id: str, *args, max_retries: int = 10, log: str | None = '', **kwargs
    ) -> Response: ...

    def filter_alphas_limited(self, *args, log: str | None = '', **kwargs) -> Response: ...

    def filter_alphas(
        self,
        *args,
        limit: int = 100,
        offset: int = 0,
        log: str | None = '',
        log_gap: int = 100,
        **kwargs,
    ) -> Generator[Response, None, None]: ...

    def patch_properties(self, alpha_id: str, *args, log: str | None = '', **kwargs) -> Response: ...

    async def check(
        self, alpha_id: str, *args, log: str | None = '', retry_log: str | None = None, **kwargs
    ) -> Response | None: ...

    async def concurrent_check(
        self,
        alpha_ids: Iterable[str],
        concurrency: int,
        *args,
        return_exceptions: bool = False,
        log: str | None = '',
        log_gap: int = 100,
        **kwargs,
    ) -> list[Response | BaseException]: ...

    def sc_check(
        self,
        alpha_id: str,
        *,
        threshold: float = 0.7,
        correlation_type: str = 'self',
        cache_dir: str | Path | None = None,
        refresh_os_pool: bool = True,
        log: str | None = '',
    ) -> dict[str, Any]: ...

    def sc_check_batch(
        self,
        alpha_ids: Iterable[str],
        *,
        threshold: float = 0.7,
        correlation_type: str = 'self',
        cache_dir: str | Path | None = None,
        refresh_os_pool: bool = True,
        workers: int = 5,
        return_exceptions: bool = False,
        log: str | None = '',
    ) -> list[dict[str, Any] | BaseException]: ...

    def ppac_check(
        self,
        alpha_id: str,
        *,
        threshold: float = 0.5,
        cache_dir: str | Path | None = None,
        refresh_os_pool: bool = True,
        log: str | None = '',
    ) -> dict[str, Any]: ...

    def ppac_check_batch(
        self,
        alpha_ids: Iterable[str],
        *,
        threshold: float = 0.5,
        cache_dir: str | Path | None = None,
        refresh_os_pool: bool = True,
        workers: int = 5,
        return_exceptions: bool = False,
        log: str | None = '',
    ) -> list[dict[str, Any] | BaseException]: ...

    def pc_check(
        self,
        alpha_id: str,
        *,
        threshold: float = 0.7,
        max_wait_seconds: float = 3600,
        poll_interval: float = 30,
        log: str | None = '',
    ) -> dict[str, Any]: ...

    async def submit(
        self, alpha_id: str, *args, log: str | None = '', retry_log: str | None = None, **kwargs
    ) -> Response | None: ...
