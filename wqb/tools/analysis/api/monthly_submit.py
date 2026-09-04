"""Monthly submit analysis API protocols and types."""
from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from typing import Any, Protocol

__all__ = [
    'AlphaFilterSession',
    'DEFAULT_MAX_ALPHAS',
    'DEFAULT_PAGE_SIZE',
    'DEFAULT_REGION_ORDER',
    'DEFAULT_REQUEST_DELAY',
    'DEFAULT_START_DATE',
    'MonthlySubmitAnalysisAPI',
]

DEFAULT_REGION_ORDER = [
    'USA',
    'EUR',
    'GLB',
    'ASI',
    'IND',
    'DEU',
    'JPN',
    'CHN',
    'AMR',
    'KOR',
]

DEFAULT_START_DATE = '2025-12-01'
DEFAULT_PAGE_SIZE = 100
DEFAULT_MAX_ALPHAS = 50_000
DEFAULT_REQUEST_DELAY = 0.3


class AlphaFilterSession(Protocol):
    """BRAIN client with ``filter_alphas`` (e.g. ``WQBSession``)."""

    def filter_alphas(self, *args, **kwargs) -> Iterator[Any]: ...


class MonthlySubmitAnalysisAPI(Protocol):
    """Monthly submitted alpha counts by region."""

    def fetch_submitted_alphas(
        self,
        session: AlphaFilterSession,
        *,
        start_date: str | None = DEFAULT_START_DATE,
        end_date: str | None = None,
        regular_only: bool = False,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_alphas: int = DEFAULT_MAX_ALPHAS,
        request_delay: float = DEFAULT_REQUEST_DELAY,
    ) -> list[dict[str, Any]]: ...

    def aggregate_month_region(
        self,
        alphas: Iterable[dict[str, Any]],
        *,
        region_order: Sequence[str] | None = None,
    ) -> dict[str, Any]: ...

    def monthly_submit_count_by_region_json(
        self,
        session: AlphaFilterSession,
        *,
        start_date: str | None = DEFAULT_START_DATE,
        end_date: str | None = None,
        regular_only: bool = False,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_alphas: int = DEFAULT_MAX_ALPHAS,
        request_delay: float = DEFAULT_REQUEST_DELAY,
    ) -> dict[str, Any]: ...

    def format_pivot_table(self, result: dict[str, Any]) -> str: ...

    def print_pivot_table(self, result: dict[str, Any]) -> None: ...

    def print_monthly_submit_report(self, result: dict[str, Any]) -> None: ...
