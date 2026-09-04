"""Default ``PnlCorrelationAPI`` implementation."""
from __future__ import annotations

from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from ..api.pnl_matrix import (
    DEFAULT_ALPHA_WORKERS,
    DEFAULT_PNL_WORKERS,
    DEFAULT_YEARS,
    CorrelationMatrixResult,
    PnlInput,
    PnlSession,
)
from .core import (
    build_corr_from_series,
    fetch_alpha_pnl_series,
    pair_corr_from_series,
    pnl_to_series,
    require_pandas,
)

__all__ = [
    'DefaultPnlCorrelation',
    'default_pnl_correlation',
]


class DefaultPnlCorrelation:
    """Default implementation of ``PnlCorrelationAPI``."""

    def corr_between_alphas(
        self,
        session: PnlSession,
        alpha_id_a: str,
        alpha_id_b: str,
        *,
        years: int = DEFAULT_YEARS,
        log: str | None = None,
    ) -> float:
        a = str(alpha_id_a).strip()
        b = str(alpha_id_b).strip()
        if not a or not b:
            raise ValueError('alpha_id must be non-empty')
        ser_a = fetch_alpha_pnl_series(session, a, log=log)
        ser_b = fetch_alpha_pnl_series(session, b, log=log)
        if ser_a is None or ser_b is None:
            raise ValueError('failed to load PnL for one or both alphas')
        corr, _obs = pair_corr_from_series([ser_a, ser_b], years=years)
        return corr

    def corr_between_pnls(
        self,
        pnl_a: PnlInput,
        pnl_b: PnlInput,
        *,
        years: int = DEFAULT_YEARS,
        name_a: str = 'a',
        name_b: str = 'b',
    ) -> float:
        ser_a = pnl_to_series(pnl_a, name_a)
        ser_b = pnl_to_series(pnl_b, name_b)
        if ser_a is None or ser_b is None:
            raise ValueError('failed to parse one or both PnL inputs')
        corr, _obs = pair_corr_from_series([ser_a, ser_b], years=years)
        return corr

    def corr_matrix_alphas(
        self,
        session: PnlSession,
        alpha_ids: Sequence[str],
        *,
        years: int = DEFAULT_YEARS,
        workers: int = DEFAULT_ALPHA_WORKERS,
        log: str | None = None,
    ) -> CorrelationMatrixResult:
        require_pandas()
        import pandas as pd

        ids = [str(aid).strip() for aid in alpha_ids if str(aid).strip()]
        if len(ids) < 2:
            raise ValueError('alpha_ids must contain at least 2 non-empty ids')

        series_by_id: dict[str, Any] = {}
        skipped: list[str] = []

        def _fetch(aid: str):
            return aid, fetch_alpha_pnl_series(session, aid, log=log)

        worker_count = max(1, min(int(workers), len(ids)))
        if worker_count == 1:
            results = [_fetch(aid) for aid in ids]
        else:
            results = []
            with ThreadPoolExecutor(max_workers=worker_count) as pool:
                futures = {pool.submit(_fetch, aid): aid for aid in ids}
                for fut in as_completed(futures):
                    results.append(fut.result())

        for aid, ser in results:
            if ser is None or getattr(ser, 'empty', True):
                skipped.append(aid)
            else:
                series_by_id[aid] = ser

        labels = tuple(aid for aid in ids if aid in series_by_id)
        if len(labels) < 2:
            return CorrelationMatrixResult(pd.DataFrame(), labels, tuple(skipped), 0)

        corr_df, obs = build_corr_from_series(
            [series_by_id[aid] for aid in labels],
            years=years,
        )
        if not corr_df.empty:
            corr_df.index = list(labels)
            corr_df.columns = list(labels)

        return CorrelationMatrixResult(
            matrix=corr_df,
            labels=labels,
            skipped=tuple(skipped),
            observations=obs,
        )

    def corr_matrix_pnls(
        self,
        pnls: Sequence[PnlInput],
        *,
        names: Sequence[str] | None = None,
        years: int = DEFAULT_YEARS,
        workers: int = DEFAULT_PNL_WORKERS,
    ) -> CorrelationMatrixResult:
        require_pandas()
        import pandas as pd

        if len(pnls) < 2:
            raise ValueError('pnls must contain at least 2 items')

        if names is None:
            labels_in = [str(i) for i in range(len(pnls))]
        else:
            labels_in = [str(n).strip() for n in names]
            if len(labels_in) != len(pnls):
                raise ValueError('names length must match pnls length')

        def _parse(_idx: int, pnl: PnlInput, label: str):
            return label, pnl_to_series(pnl, label)

        worker_count = max(1, min(int(workers), len(pnls)))
        if worker_count == 1:
            parsed = [_parse(i, pnl, label) for i, (pnl, label) in enumerate(zip(pnls, labels_in))]
        else:
            parsed = []
            with ThreadPoolExecutor(max_workers=worker_count) as pool:
                futures = {
                    pool.submit(_parse, i, pnl, label): label
                    for i, (pnl, label) in enumerate(zip(pnls, labels_in))
                }
                for fut in as_completed(futures):
                    parsed.append(fut.result())

        series_by_label: dict[str, Any] = {}
        skipped: list[str] = []
        for label, ser in parsed:
            if ser is None or getattr(ser, 'empty', True):
                skipped.append(label)
            else:
                series_by_label[label] = ser

        labels = tuple(label for label in labels_in if label in series_by_label)
        if len(labels) < 2:
            return CorrelationMatrixResult(pd.DataFrame(), labels, tuple(skipped), 0)

        corr_df, obs = build_corr_from_series(
            [series_by_label[label] for label in labels],
            years=years,
        )
        if not corr_df.empty:
            corr_df.index = list(labels)
            corr_df.columns = list(labels)

        return CorrelationMatrixResult(
            matrix=corr_df,
            labels=labels,
            skipped=tuple(skipped),
            observations=obs,
        )


default_pnl_correlation = DefaultPnlCorrelation()
