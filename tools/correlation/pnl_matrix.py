"""Build Pearson correlation matrix from alpha PnL recordsets."""
from __future__ import annotations

import json
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Protocol

from requests import Response

__all__ = [
    'PnlSession',
    'corr_df_to_json',
    'pnl_corr_matrix',
    'pnl_corr_matrix_json',
]

DEFAULT_PNL_MATRIX_WORKERS = 5
DEFAULT_PNL_LOOKBACK_YEARS = 4


class PnlSession(Protocol):
    def get_pnl(self, alpha_id: str, *args, **kwargs) -> Response: ...


def _require_pandas():
    try:
        import pandas as pd  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            'tools.correlation requires pandas. Install with: pip install pandas'
        ) from exc


def _normalize_dt_index(idx):
    import pandas as pd

    dti = pd.DatetimeIndex(pd.to_datetime(idx, errors='coerce', utc=True))
    if dti.tz is not None:
        dti = dti.tz_convert('UTC').tz_localize(None)
    return dti.normalize()


def _pnl_payload_to_series(payload: dict[str, Any], alpha_id: str):
    import pandas as pd

    records = payload.get('records') or []
    if not records:
        return None

    props = (payload.get('schema') or {}).get('properties') or []
    col_names = [p.get('name') for p in props if isinstance(p, dict) and p.get('name')]
    if not col_names:
        return None

    df = pd.DataFrame(records, columns=col_names)
    dt_col = 'date' if 'date' in df.columns else ('Date' if 'Date' in df.columns else None)
    if not dt_col or 'pnl' not in df.columns:
        return None

    tmp = df[[dt_col, 'pnl']].copy()
    tmp[dt_col] = pd.to_datetime(tmp[dt_col], errors='coerce')
    tmp = tmp.dropna(subset=[dt_col]).sort_values(dt_col)
    ser = pd.to_numeric(tmp.set_index(dt_col)['pnl'], errors='coerce')
    ser.name = str(alpha_id).strip()
    ser = ser.dropna()
    return ser if not ser.empty else None


def fetch_pnl_series(session: PnlSession, alpha_id: str, *, log: str | None = None):
    """Fetch one alpha PnL via ``session.get_pnl`` and return cumulative series."""
    aid = str(alpha_id).strip()
    if not aid:
        return None
    resp = session.get_pnl(aid, log=log)
    resp.raise_for_status()
    return _pnl_payload_to_series(resp.json(), aid)


def _build_corr_from_series(
    series_list: list,
    *,
    years: int,
    absolute: bool,
):
    import pandas as pd

    if len(series_list) < 2:
        return pd.DataFrame(), 0

    combined = pd.concat(series_list, axis=1, join='inner')
    if combined.empty or len(combined) < 2:
        return pd.DataFrame(), 0

    if years > 0:
        cutoff = combined.index.max() - pd.DateOffset(years=years)
        combined = combined[combined.index > cutoff]

    if combined.empty or len(combined) < 2:
        return pd.DataFrame(), 0

    rets = combined - combined.ffill().shift(1)
    rets = rets.dropna(how='all')
    if len(rets) < 2:
        return pd.DataFrame(), 0

    corr = rets.corr()
    if absolute:
        corr = corr.abs()
    return corr, len(rets)


def corr_df_to_json(corr_df) -> dict[str, dict[str, float | None]]:
    """Convert correlation DataFrame to nested JSON-serializable dict."""
    import math

    out: dict[str, dict[str, float | None]] = {}
    for row_id in corr_df.index:
        row_key = str(row_id)
        out[row_key] = {}
        for col_id in corr_df.columns:
            val = corr_df.loc[row_id, col_id]
            if val is None or (isinstance(val, float) and math.isnan(val)):
                out[row_key][str(col_id)] = None
            else:
                out[row_key][str(col_id)] = round(float(val), 6)
    return out


def pnl_corr_matrix(
    session: PnlSession,
    alpha_ids: Sequence[str],
    *,
    years: int = DEFAULT_PNL_LOOKBACK_YEARS,
    workers: int = DEFAULT_PNL_MATRIX_WORKERS,
    absolute: bool = False,
    log: str | None = None,
) -> tuple[Any, list[str], int]:
    """
    Fetch PnL for ``alpha_ids`` and build daily-return Pearson correlation matrix.

    Returns ``(corr_df, skipped_alpha_ids, observation_count)``.
    """
    _require_pandas()

    ids = [str(aid).strip() for aid in alpha_ids if str(aid).strip()]
    if len(ids) < 2:
        import pandas as pd

        return pd.DataFrame(), list(ids), 0

    series_by_id: dict[str, Any] = {}
    skipped: list[str] = []

    def _fetch(aid: str):
        return aid, fetch_pnl_series(session, aid, log=log)

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
        if ser is None or ser.empty:
            skipped.append(aid)
        else:
            ser.index = _normalize_dt_index(ser.index)
            series_by_id[aid] = ser

    ordered = [aid for aid in ids if aid in series_by_id]
    corr_df, obs = _build_corr_from_series(
        [series_by_id[aid] for aid in ordered],
        years=years,
        absolute=absolute,
    )
    if not corr_df.empty:
        corr_df.index = ordered
        corr_df.columns = ordered
    return corr_df, skipped, obs


def pnl_corr_matrix_json(
    session: PnlSession,
    alpha_ids: Sequence[str],
    *,
    years: int = DEFAULT_PNL_LOOKBACK_YEARS,
    workers: int = DEFAULT_PNL_MATRIX_WORKERS,
    absolute: bool = False,
    log: str | None = None,
) -> dict[str, Any]:
    """
    Like ``pnl_corr_matrix`` but returns a JSON-ready dict.

    Example::

        result = pnl_corr_matrix_json(wqbs, ['abc', 'def'])
        print(json.dumps(result, indent=2))
    """
    corr_df, skipped, obs = pnl_corr_matrix(
        session,
        alpha_ids,
        years=years,
        workers=workers,
        absolute=absolute,
        log=log,
    )
    alpha_ids_out = [str(x) for x in corr_df.index.tolist()] if not corr_df.empty else []
    payload = {
        'alpha_ids': alpha_ids_out,
        'skipped': skipped,
        'years': years,
        'absolute': absolute,
        'observations': obs,
        'matrix': corr_df_to_json(corr_df) if not corr_df.empty else {},
    }
    return payload


def dumps_pnl_corr_matrix_json(*args, **kwargs) -> str:
    """Return ``json.dumps(pnl_corr_matrix_json(...))``."""
    return json.dumps(pnl_corr_matrix_json(*args, **kwargs), indent=2)
