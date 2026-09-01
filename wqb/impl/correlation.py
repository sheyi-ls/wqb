"""Self-correlation (local) and production-correlation (platform) checks."""
from __future__ import annotations

import json
import pickle
import time
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Literal

from requests import Response

from ..common.urls import (
    URL_ALPHAS_ALPHAID,
    URL_ALPHAS_ALPHAID_CORRELATIONS_PROD,
    URL_ALPHAS_ALPHAID_PNL,
    URL_USERS_SELF_ALPHAS,
)
from ..common.wait_get import wait_get

__all__ = [
    'DEFAULT_OS_CACHE_DIR',
    'DEFAULT_PPAC_THRESHOLD',
    'DEFAULT_SC_BATCH_WORKERS',
    'CorrelationType',
    'prod_correlation_peak',
    'sc_check',
    'sc_check_batch',
    'ppac_check',
    'ppac_check_batch',
    'pc_check',
    'sync_os_pool',
]

DEFAULT_PPAC_THRESHOLD = 0.5
DEFAULT_SC_BATCH_WORKERS = 5

CorrelationType = Literal['self', 'powerpool', 'all']

DEFAULT_OS_CACHE_DIR = Path.home() / '.cache' / 'wqb' / 'os_pool'
SELF_CORR_TAG = 'SelfCorr'
PPAC_CORR_TAG = 'PPAC'
OS_LOOKBACK_YEARS = 4
PNL_FETCH_WORKERS = 5


def _require_pandas():
    try:
        import pandas as pd  # noqa: F401
        import numpy as np  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            'sc_check requires pandas and numpy. Install with: pip install "wqb[correlation]"'
        ) from exc


def prod_correlation_peak(data: dict[str, Any]) -> float:
    """Peak |correlation| from BRAIN ``/correlations/prod`` JSON."""
    mx = float(data.get('max') or 0)
    mn = float(data.get('min') or 0)
    return max(abs(mx), abs(mn))


def _normalize_dt_index(idx):
    import pandas as pd

    dti = pd.DatetimeIndex(pd.to_datetime(idx, errors='coerce', utc=True))
    if dti.tz is not None:
        dti = dti.tz_convert('UTC').tz_localize(None)
    return dti.normalize()


def _get_alpha_pnl(session, alpha_id: str):
    import pandas as pd

    resp = wait_get(session, URL_ALPHAS_ALPHAID_PNL.format(alpha_id), max_retries=30)
    pnl = resp.json()
    df = pd.DataFrame(pnl['records'], columns=[item['name'] for item in pnl['schema']['properties']])
    df = df.rename(columns={'date': 'Date', 'pnl': alpha_id})
    return df[['Date', alpha_id]]


def _get_os_alphas(session, *, limit: int = 100, get_first: bool = False) -> list[dict[str, Any]]:
    fetched: list[dict[str, Any]] = []
    offset = 0
    total_alphas = limit
    while len(fetched) < total_alphas:
        url = (
            f"{URL_USERS_SELF_ALPHAS}?stage=OS&limit={limit}&offset={offset}"
            f"&order=-dateSubmitted"
        )
        res = wait_get(session, url, max_retries=30)
        body = res.json()
        if 'count' not in body:
            raise RuntimeError(f'Unexpected OS alpha list response: {str(body)[:200]}')
        if offset == 0:
            total_alphas = body['count']
        alphas = body.get('results', [])
        fetched.extend(alphas)
        if len(alphas) < limit:
            break
        offset += limit
        if get_first:
            break
    return fetched[:total_alphas]


def _save_pickle(obj: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


def _load_pickle(path: Path) -> object:
    with path.open('rb') as f:
        return pickle.load(f)


def sync_os_pool(
    session,
    cache_dir: Path | str = DEFAULT_OS_CACHE_DIR,
    *,
    incremental: bool = True,
) -> tuple[dict[str, list[str]], Any]:
    """Download / refresh submitted OS alpha PnL cache used by ``sc_check``."""
    _require_pandas()
    import pandas as pd

    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    ids_path = cache_dir / 'os_alpha_ids.pickle'
    pnls_path = cache_dir / 'os_alpha_pnls.pickle'
    ppac_path = cache_dir / 'ppac_alpha_ids.pickle'

    os_alpha_ids: dict[str, list[str]] | None = None
    os_alpha_pnls: pd.DataFrame | None = None
    exist_alpha: list[str] = []
    ppac_alpha_ids: list[str] = []

    if incremental and ids_path.exists() and pnls_path.exists():
        try:
            os_alpha_ids = _load_pickle(ids_path)
            os_alpha_pnls = _load_pickle(pnls_path)
            ppac_alpha_ids = list(_load_pickle(ppac_path)) if ppac_path.exists() else []
            exist_alpha = [a for ids in os_alpha_ids.values() for a in ids]
        except Exception:
            os_alpha_ids = None
            os_alpha_pnls = None
            exist_alpha = []
            ppac_alpha_ids = []

    if os_alpha_ids is None:
        alphas = _get_os_alphas(session, limit=100, get_first=False)
    else:
        alphas = _get_os_alphas(session, limit=30, get_first=True)

    alphas = [item for item in alphas if item['id'] not in exist_alpha]
    ppac_alpha_ids = list(ppac_alpha_ids)
    ppac_alpha_ids.extend(
        item['id']
        for item in alphas
        for cls in item.get('classifications', [])
        if cls.get('name') == 'Power Pool Alpha'
    )

    if os_alpha_ids is None:
        os_alpha_ids = defaultdict(list)
    if os_alpha_pnls is None:
        os_alpha_pnls = pd.DataFrame()

    new_alphas = [item for item in alphas if item['id'] not in os_alpha_pnls.columns]
    for item_alpha in new_alphas:
        os_alpha_ids[item_alpha['settings']['region']].append(item_alpha['id'])

    if new_alphas:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _fetch_pnl(alpha_id: str):
            return _get_alpha_pnl(session, alpha_id).set_index('Date')

        frames = []
        workers = max(1, min(PNL_FETCH_WORKERS, len(new_alphas)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_fetch_pnl, item['id']): item['id'] for item in new_alphas}
            for fut in as_completed(futures):
                frames.append(fut.result())
        os_alpha_pnls = pd.concat([os_alpha_pnls] + frames, axis=1)

    os_alpha_pnls.sort_index(inplace=True)
    _save_pickle(dict(os_alpha_ids), ids_path)
    _save_pickle(os_alpha_pnls, pnls_path)
    _save_pickle(ppac_alpha_ids, ppac_path)
    return dict(os_alpha_ids), os_alpha_pnls


def _load_os_returns(
    cache_dir: Path | str,
    *,
    correlation_type: CorrelationType = 'self',
):
    _require_pandas()
    import pandas as pd

    cache_dir = Path(cache_dir)
    os_alpha_ids = _load_pickle(cache_dir / 'os_alpha_ids.pickle')
    os_alpha_pnls = _load_pickle(cache_dir / 'os_alpha_pnls.pickle')
    ppac_alpha_ids = _load_pickle(cache_dir / 'ppac_alpha_ids.pickle')

    if not isinstance(os_alpha_ids, dict):
        os_alpha_ids = {}
    os_alpha_ids = {k: list(v) for k, v in os_alpha_ids.items()}
    raw_snapshot = {k: list(v) for k, v in os_alpha_ids.items()}

    if not isinstance(ppac_alpha_ids, (list, tuple, set)):
        ppac_alpha_ids = []
    pp_set = set(ppac_alpha_ids)

    if correlation_type == 'self':
        for region in os_alpha_ids:
            os_alpha_ids[region] = [a for a in os_alpha_ids[region] if a not in pp_set]
        if sum(len(v) for v in os_alpha_ids.values()) == 0:
            os_alpha_ids = raw_snapshot
    elif correlation_type == 'powerpool':
        for region in os_alpha_ids:
            os_alpha_ids[region] = [a for a in os_alpha_ids[region] if a in pp_set]
        if sum(len(v) for v in os_alpha_ids.values()) == 0:
            os_alpha_ids = raw_snapshot

    exist_alpha = [a for ids in os_alpha_ids.values() for a in ids]
    os_alpha_pnls = os_alpha_pnls[exist_alpha]
    os_alpha_rets = os_alpha_pnls - os_alpha_pnls.ffill().shift(1)
    os_alpha_rets.index = _normalize_dt_index(os_alpha_rets.index)
    cutoff = os_alpha_rets.index.max() - pd.DateOffset(years=OS_LOOKBACK_YEARS)
    os_alpha_rets = os_alpha_rets[os_alpha_rets.index > cutoff]
    return os_alpha_ids, os_alpha_rets


def _resolve_os_rets_columns(candidates: list[Any], os_alpha_rets) -> list[Any]:
    if os_alpha_rets is None or os_alpha_rets.shape[1] == 0:
        return []
    by_key = {str(c): c for c in os_alpha_rets.columns}
    out: list[Any] = []
    seen: set[Any] = set()
    for c in candidates:
        col = by_key.get(str(c))
        if col is not None and col not in seen:
            seen.add(col)
            out.append(col)
    return out


def calc_self_corr(
    session,
    alpha_id: str,
    *,
    os_alpha_rets,
    os_alpha_ids: dict[str, list[str]],
    alpha_result: dict[str, Any] | None = None,
    candidate_pnl=None,
) -> float:
    """Max correlation of target alpha vs OS pool (last 4y daily returns)."""
    _require_pandas()
    import numpy as np
    import pandas as pd

    if alpha_result is None:
        resp = wait_get(session, URL_ALPHAS_ALPHAID.format(alpha_id), max_retries=30)
        alpha_result = resp.json()

    aid_col = str(alpha_result.get('id', alpha_id)).strip()
    if candidate_pnl is not None:
        pnl_series = candidate_pnl.sort_index()
    else:
        pnl_df = _get_alpha_pnl(session, aid_col).set_index('Date')
        pnl_series = pnl_df[aid_col if aid_col in pnl_df.columns else str(alpha_id).strip()]

    alpha_rets = pnl_series - pnl_series.ffill().shift(1)
    alpha_rets.index = _normalize_dt_index(alpha_rets.index)
    cutoff = alpha_rets.index.max() - pd.DateOffset(years=OS_LOOKBACK_YEARS)
    alpha_rets = alpha_rets[alpha_rets.index > cutoff]

    region = alpha_result.get('settings', {}).get('region')
    candidates = list(os_alpha_ids.get(region) or [])
    if not candidates:
        candidates = [aid for ids in os_alpha_ids.values() for aid in ids]
    cols = _resolve_os_rets_columns(candidates, os_alpha_rets)
    if not cols:
        return 0.0

    os_block = os_alpha_rets[cols].copy()
    os_block.index = _normalize_dt_index(os_block.index)
    alpha_rets = alpha_rets.copy()
    alpha_rets.index = _normalize_dt_index(alpha_rets.index)

    if alpha_rets.size == 0 or os_block.shape[0] == 0 or os_block.shape[1] == 0:
        return 0.0

    self_corr = os_block.corrwith(alpha_rets).max()
    if np.isnan(self_corr):
        return 0.0
    return float(self_corr)


def _sc_check_one(
    session,
    alpha_id: str,
    *,
    threshold: float,
    correlation_type: CorrelationType,
    os_alpha_ids: dict[str, list[str]],
    os_alpha_rets,
    pool_size: int | None = None,
) -> dict[str, Any]:
    resp = wait_get(session, URL_ALPHAS_ALPHAID.format(alpha_id), max_retries=30)
    alpha_result = resp.json()
    pnl_df = _get_alpha_pnl(session, alpha_id).set_index('Date')
    aid = str(alpha_id).strip()
    pnl_series = pnl_df[aid] if aid in pnl_df.columns else pnl_df.iloc[:, 0]

    max_corr = calc_self_corr(
        session,
        alpha_id,
        os_alpha_rets=os_alpha_rets,
        os_alpha_ids=os_alpha_ids,
        alpha_result=alpha_result,
        candidate_pnl=pnl_series,
    )
    if pool_size is None:
        pool_size = sum(len(v) for v in os_alpha_ids.values())

    return {
        'alpha_id': alpha_id,
        'threshold': threshold,
        'correlation_type': correlation_type,
        'max_correlation': max_corr,
        'passes_check': max_corr < threshold,
        'local_calculation': True,
        'pool_size': pool_size,
    }


def _ppac_result_from_sc(result: dict[str, Any]) -> dict[str, Any]:
    max_corr = result['max_correlation']
    return {
        'alpha_id': result['alpha_id'],
        'threshold': result['threshold'],
        'ppac_correlation': max_corr,
        'max_correlation': max_corr,
        'passes_check': result['passes_check'],
        'local_calculation': True,
        'pool_size': result['pool_size'],
        'correlation_type': 'powerpool',
    }


def _map_parallel(
    items: list[str],
    fn,
    *,
    workers: int,
    return_exceptions: bool,
) -> list[dict[str, Any] | BaseException]:
    workers = max(1, int(workers))
    if workers == 1 or len(items) <= 1:
        out: list[dict[str, Any] | BaseException] = []
        for item in items:
            try:
                out.append(fn(item))
            except Exception as exc:
                if return_exceptions:
                    out.append(exc)
                else:
                    raise
        return out

    from concurrent.futures import ThreadPoolExecutor, as_completed

    results: list[dict[str, Any] | BaseException | None] = [None] * len(items)
    index = {item: i for i, item in enumerate(items)}
    with ThreadPoolExecutor(max_workers=min(workers, len(items))) as pool:
        futures = {pool.submit(fn, item): item for item in items}
        for fut in as_completed(futures):
            item = futures[fut]
            i = index[item]
            try:
                results[i] = fut.result()
            except Exception as exc:
                if return_exceptions:
                    results[i] = exc
                else:
                    raise
    return results  # type: ignore[return-value]


def _local_corr_batch(
    session,
    alpha_ids: Iterable[str],
    *,
    threshold: float,
    correlation_type: CorrelationType,
    cache_dir: Path | str,
    refresh_os_pool: bool,
    workers: int,
    return_exceptions: bool,
) -> list[dict[str, Any] | BaseException]:
    _require_pandas()

    ids = [str(a).strip() for a in alpha_ids if str(a).strip()]
    if not ids:
        return []

    cache_dir = Path(cache_dir)
    if refresh_os_pool:
        sync_os_pool(session, cache_dir, incremental=True)

    os_alpha_ids, os_alpha_rets = _load_os_returns(
        cache_dir, correlation_type=correlation_type
    )
    pool_size = sum(len(v) for v in os_alpha_ids.values())

    def _task(aid: str) -> dict[str, Any]:
        return _sc_check_one(
            session,
            aid,
            threshold=threshold,
            correlation_type=correlation_type,
            os_alpha_ids=os_alpha_ids,
            os_alpha_rets=os_alpha_rets,
            pool_size=pool_size,
        )

    return _map_parallel(ids, _task, workers=workers, return_exceptions=return_exceptions)


def sc_check(
    session,
    alpha_id: str,
    *,
    threshold: float = 0.7,
    correlation_type: CorrelationType = 'self',
    cache_dir: Path | str = DEFAULT_OS_CACHE_DIR,
    refresh_os_pool: bool = True,
) -> dict[str, Any]:
    """
    Local self-correlation check (no platform SC API).

    Mirrors ``WorldQuant/RA/sc_checker.py`` ``calc_self_corr`` semantics:
    compare target alpha daily returns (last 4 years) against a cached OS PnL
    pool. ``correlation_type='self'`` excludes Power Pool alphas from the pool.
    """
    _require_pandas()

    cache_dir = Path(cache_dir)
    if refresh_os_pool:
        sync_os_pool(session, cache_dir, incremental=True)

    os_alpha_ids, os_alpha_rets = _load_os_returns(
        cache_dir, correlation_type=correlation_type
    )
    return _sc_check_one(
        session,
        alpha_id,
        threshold=threshold,
        correlation_type=correlation_type,
        os_alpha_ids=os_alpha_ids,
        os_alpha_rets=os_alpha_rets,
    )


def sc_check_batch(
    session,
    alpha_ids: Iterable[str],
    *,
    threshold: float = 0.7,
    correlation_type: CorrelationType = 'self',
    cache_dir: Path | str = DEFAULT_OS_CACHE_DIR,
    refresh_os_pool: bool = True,
    workers: int = DEFAULT_SC_BATCH_WORKERS,
    return_exceptions: bool = False,
) -> list[dict[str, Any] | BaseException]:
    """
    Batch local self-correlation checks.

    Syncs the OS pool once (when *refresh_os_pool*), loads returns once, then
    evaluates each alpha. Use *workers* > 1 for ``ThreadPoolExecutor`` parallelism
    (shared session; same pattern as ``RA/sc_checker.py``).
    """
    return _local_corr_batch(
        session,
        alpha_ids,
        threshold=threshold,
        correlation_type=correlation_type,
        cache_dir=cache_dir,
        refresh_os_pool=refresh_os_pool,
        workers=workers,
        return_exceptions=return_exceptions,
    )


def ppac_check(
    session,
    alpha_id: str,
    *,
    threshold: float = DEFAULT_PPAC_THRESHOLD,
    cache_dir: Path | str = DEFAULT_OS_CACHE_DIR,
    refresh_os_pool: bool = True,
) -> dict[str, Any]:
    """
    Local PPAC (Power Pool Alpha Correlation) check.

    Compare target alpha daily returns (last 4 years) against submitted OS
    alphas tagged ``Power Pool Alpha`` only. Same math as ``sc_check`` but
    with ``correlation_type='powerpool'`` (see ``RA/sc_checker.py`` PPAC path).
    """
    result = sc_check(
        session,
        alpha_id,
        threshold=threshold,
        correlation_type='powerpool',
        cache_dir=cache_dir,
        refresh_os_pool=refresh_os_pool,
    )
    return _ppac_result_from_sc(result)


def ppac_check_batch(
    session,
    alpha_ids: Iterable[str],
    *,
    threshold: float = DEFAULT_PPAC_THRESHOLD,
    cache_dir: Path | str = DEFAULT_OS_CACHE_DIR,
    refresh_os_pool: bool = True,
    workers: int = DEFAULT_SC_BATCH_WORKERS,
    return_exceptions: bool = False,
) -> list[dict[str, Any] | BaseException]:
    """Batch PPAC checks; see ``sc_check_batch`` for pooling and *workers*."""
    raw = _local_corr_batch(
        session,
        alpha_ids,
        threshold=threshold,
        correlation_type='powerpool',
        cache_dir=cache_dir,
        refresh_os_pool=refresh_os_pool,
        workers=workers,
        return_exceptions=return_exceptions,
    )
    out: list[dict[str, Any] | BaseException] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(_ppac_result_from_sc(item))
        else:
            out.append(item)
    return out


def pc_check(
    session,
    alpha_id: str,
    *,
    threshold: float = 0.7,
    max_wait_seconds: float = 3600,
    poll_interval: float = 30,
    log: str | None = '',
) -> dict[str, Any]:
    """
    Production-correlation check via BRAIN platform API.

    Polls ``GET /alphas/{id}/correlations/prod`` until data is ready or
    *max_wait_seconds* elapses (platform may return empty body while computing).
    """
    url = URL_ALPHAS_ALPHAID_CORRELATIONS_PROD.format(alpha_id)
    start = time.time()
    attempt = 0
    consecutive_empty = 0

    while True:
        elapsed = time.time() - start
        if elapsed >= max_wait_seconds:
            return {
                'alpha_id': alpha_id,
                'threshold': threshold,
                'max_correlation': None,
                'passes_check': None,
                'status': 'pending',
                'local_calculation': False,
                'message': (
                    f'Production correlation not available after {int(elapsed)}s; retry later.'
                ),
                'correlation_data': {'max': None, 'records': []},
            }

        attempt += 1
        resp: Response = session.get(url)

        if resp.status_code == 401:
            session.auth_request()
            continue
        if resp.status_code == 429:
            wait = float(resp.headers.get('Retry-After', poll_interval))
            time.sleep(wait)
            continue
        resp.raise_for_status()

        text = (resp.text or '').strip()
        if not text:
            consecutive_empty += 1
            time.sleep(poll_interval)
            continue

        try:
            data = resp.json()
        except json.JSONDecodeError:
            time.sleep(poll_interval)
            continue

        if data.get('max') is not None or data.get('min') is not None:
            peak = prod_correlation_peak(data)
            return {
                'alpha_id': alpha_id,
                'threshold': threshold,
                'max_correlation': peak,
                'passes_check': peak < threshold,
                'status': 'complete',
                'local_calculation': False,
                'elapsed_seconds': elapsed,
                'attempts': attempt,
                'correlation_data': data,
            }

        retry_after = resp.headers.get('Retry-After')
        if retry_after:
            time.sleep(float(retry_after))
        else:
            time.sleep(poll_interval)
