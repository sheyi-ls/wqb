"""Default ``MonthlySubmitAnalysisAPI`` implementation."""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from ..api.monthly_submit import (
    DEFAULT_MAX_ALPHAS,
    DEFAULT_PAGE_SIZE,
    DEFAULT_REQUEST_DELAY,
    DEFAULT_START_DATE,
    AlphaFilterSession,
)
from .core import (
    aggregate_month_region,
    fetch_submitted_alphas,
    format_pivot_table,
    print_monthly_submit_report,
    print_pivot_table,
)

__all__ = [
    'DefaultMonthlySubmitAnalysis',
    'default_monthly_submit_analysis',
]


class DefaultMonthlySubmitAnalysis:
    """Default implementation of ``MonthlySubmitAnalysisAPI``."""

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
    ) -> list[dict[str, Any]]:
        return fetch_submitted_alphas(
            session,
            start_date=start_date,
            end_date=end_date,
            regular_only=regular_only,
            page_size=page_size,
            max_alphas=max_alphas,
            request_delay=request_delay,
        )

    def aggregate_month_region(
        self,
        alphas: Iterable[dict[str, Any]],
        *,
        region_order: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        return aggregate_month_region(alphas, region_order=region_order)

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
    ) -> dict[str, Any]:
        """
        Fetch OS alphas and return monthly submit counts by region as JSON.

        Uses wqb ``session.filter_alphas`` and returns structured JSON.
        """
        alphas = self.fetch_submitted_alphas(
            session,
            start_date=start_date,
            end_date=end_date,
            regular_only=regular_only,
            page_size=page_size,
            max_alphas=max_alphas,
            request_delay=request_delay,
        )
        regular_n = sum(1 for a in alphas if a.get('type') == 'REGULAR')
        super_n = sum(1 for a in alphas if a.get('type') == 'SUPER')
        agg = self.aggregate_month_region(alphas)

        return {
            'start_date': start_date,
            'end_date': end_date,
            'regular_only': regular_only,
            'total_alphas': len(alphas),
            'regular_count': regular_n,
            'super_count': super_n,
            **agg,
        }

    def format_pivot_table(self, result: dict[str, Any]) -> str:
        return format_pivot_table(result)

    def print_pivot_table(self, result: dict[str, Any]) -> None:
        print_pivot_table(result)

    def print_monthly_submit_report(self, result: dict[str, Any]) -> None:
        print_monthly_submit_report(result)


default_monthly_submit_analysis = DefaultMonthlySubmitAnalysis()
