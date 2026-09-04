"""Internal PnL parsing and correlation math."""
from __future__ import annotations

import json
from typing import Any

__all__ = [
    'build_corr_from_series',
    'fetch_alpha_pnl_series',
    'normalize_dt_index',
    'pair_corr_from_series',
    'pnl_to_series',
    'require_pandas',
]


def require_pandas():
    try:
        import pandas as pd  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            'tools.correlation requires pandas. Install with: pip install pandas'
        ) from exc


def normalize_dt_index(idx):
    import pandas as pd

    dti = pd.DatetimeIndex(pd.to_datetime(idx, errors='coerce', utc=True))
    if dti.tz is not None:
        dti = dti.tz_convert('UTC').tz_localize(None)
    return dti.normalize()


def pnl_payload_to_series(payload: dict[str, Any], name: str):
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
    ser.name = str(name).strip()
    ser = ser.dropna()
    return ser if not ser.empty else None


def pnl_to_series(pnl: Any, name: str):
    """Parse cumulative PnL into a daily-indexed Series."""
    require_pandas()
    import pandas as pd

    label = str(name).strip()
    if label == '':
        raise ValueError('name must be non-empty')

    if isinstance(pnl, pd.Series):
        ser = pd.to_numeric(pnl, errors='coerce').dropna()
        if ser.empty:
            return None
        ser = ser.copy()
        ser.name = label
        ser.index = normalize_dt_index(ser.index)
        return ser

    payload = pnl
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            return None
    if not isinstance(payload, dict):
        return None

    cols = payload.get('columns')
    recs = payload.get('records')
    if cols and recs:
        df = pd.DataFrame(recs, columns=cols)
        dt_col = next((c for c in ('date', 'Date') if c in df.columns), None)
        if not dt_col or 'pnl' not in df.columns:
            return None
        tmp = df[[dt_col, 'pnl']].copy()
        tmp[dt_col] = pd.to_datetime(tmp[dt_col], errors='coerce')
        tmp = tmp.dropna(subset=[dt_col]).sort_values(dt_col)
        ser = pd.to_numeric(tmp.set_index(dt_col)['pnl'], errors='coerce').dropna()
        if ser.empty:
            return None
        ser.name = label
        ser.index = normalize_dt_index(ser.index)
        return ser

    ser = pnl_payload_to_series(payload, label)
    if ser is not None:
        ser.index = normalize_dt_index(ser.index)
    return ser


def fetch_alpha_pnl_series(session, alpha_id: str, *, log: str | None = None):
    aid = str(alpha_id).strip()
    if not aid:
        return None
    resp = session.get_pnl(aid, log=log)
    resp.raise_for_status()
    return pnl_to_series(resp.json(), aid)


def build_corr_from_series(series_list: list, *, years: int):
    import pandas as pd

    if len(series_list) < 2:
        return pd.DataFrame(), 0

    combined = pd.concat(series_list, axis=1, join='inner')
    if combined.empty or len(combined.columns) < 2:
        return pd.DataFrame(), 0

    if years > 0:
        cutoff = combined.index.max() - pd.DateOffset(years=years)
        combined = combined[combined.index > cutoff]

    if combined.empty or len(combined.columns) < 2:
        return pd.DataFrame(), 0

    rets = combined - combined.ffill().shift(1)
    rets = rets.dropna(how='all')
    if len(rets) < 2:
        return pd.DataFrame(), 0

    return rets.corr(), len(rets)


def pair_corr_from_series(series_list: list, *, years: int) -> tuple[float, int]:
    corr_df, obs = build_corr_from_series(series_list, years=years)
    if corr_df.shape != (2, 2) or obs < 2:
        raise ValueError('insufficient overlapping PnL data for correlation')
    return float(corr_df.iloc[0, 1]), obs
