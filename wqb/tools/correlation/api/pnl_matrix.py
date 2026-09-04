"""PnL correlation API protocols and types."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from requests import Response

__all__ = [
    'CorrelationMatrixResult',
    'DEFAULT_ALPHA_WORKERS',
    'DEFAULT_PNL_WORKERS',
    'DEFAULT_YEARS',
    'PnlCorrelationAPI',
    'PnlInput',
    'PnlSession',
]

DEFAULT_YEARS = 4
DEFAULT_ALPHA_WORKERS = 5
DEFAULT_PNL_WORKERS = 4

PnlInput = Any  # pandas Series | Brain recordset dict | JSON str


class PnlSession(Protocol):
    """BRAIN client with ``get_pnl`` (e.g. ``WQBSession``)."""

    def get_pnl(self, alpha_id: str, *args, **kwargs) -> Response: ...


@dataclass(frozen=True)
class CorrelationMatrixResult:
    """Pearson correlation matrix of daily PnL returns."""

    matrix: Any
    labels: tuple[str, ...]
    skipped: tuple[str, ...]
    observations: int


class PnlCorrelationAPI(Protocol):
    """Pearson correlation of daily PnL returns."""

    def corr_between_alphas(
        self,
        session: PnlSession,
        alpha_id_a: str,
        alpha_id_b: str,
        *,
        years: int = DEFAULT_YEARS,
        log: str | None = None,
    ) -> float: ...

    def corr_between_pnls(
        self,
        pnl_a: PnlInput,
        pnl_b: PnlInput,
        *,
        years: int = DEFAULT_YEARS,
        name_a: str = 'a',
        name_b: str = 'b',
    ) -> float: ...

    def corr_matrix_alphas(
        self,
        session: PnlSession,
        alpha_ids: Sequence[str],
        *,
        years: int = DEFAULT_YEARS,
        workers: int = DEFAULT_ALPHA_WORKERS,
        log: str | None = None,
    ) -> CorrelationMatrixResult: ...

    def corr_matrix_pnls(
        self,
        pnls: Sequence[PnlInput],
        *,
        names: Sequence[str] | None = None,
        years: int = DEFAULT_YEARS,
        workers: int = DEFAULT_PNL_WORKERS,
    ) -> CorrelationMatrixResult: ...
