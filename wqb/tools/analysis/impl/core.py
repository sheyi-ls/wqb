"""Internal helpers for monthly submit aggregation."""
from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Any

from ..api.monthly_submit import (
    DEFAULT_REGION_ORDER,
    AlphaFilterSession,
)

__all__ = [
    'aggregate_month_region',
    'fetch_submitted_alphas',
    'format_pivot_table',
    'parse_submitted_month',
    'print_monthly_submit_report',
    'print_pivot_table',
]


def parse_submitted_month(date_submitted: str) -> str | None:
    """Convert ``dateSubmitted`` ISO string to ``YYYY-MM``."""
    raw = str(date_submitted or '').strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m')
    except ValueError:
        if len(raw) >= 7 and raw[4] == '-' and raw[7] == '-':
            return raw[:7]
        return None


def _date_submitted_others(start_date: str | None, end_date: str | None) -> list[str]:
    params: list[str] = []
    if start_date:
        params.append(f'dateSubmitted>={start_date}T00:00:00-04:00')
    if end_date:
        params.append(f'dateSubmitted<{end_date}T00:00:00-04:00')
    return params


def normalize_alpha_row(alpha: dict[str, Any]) -> dict[str, Any]:
    settings = alpha.get('settings') or {}
    return {
        'id': alpha.get('id'),
        'region': str(settings.get('region') or 'UNKNOWN').strip().upper(),
        'type': alpha.get('type'),
        'stage': alpha.get('stage'),
        'status': alpha.get('status'),
        'dateSubmitted': alpha.get('dateSubmitted'),
    }


def _fetch_one_type(
    session: AlphaFilterSession,
    *,
    start_date: str | None,
    end_date: str | None,
    alpha_type: str | None,
    page_size: int,
    max_alphas: int,
    request_delay: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    kwargs: dict[str, Any] = {
        'type': alpha_type,
        'hidden': False,
        'order': '-dateSubmitted',
        'others': ['stage=OS', *_date_submitted_others(start_date, end_date)],
        'limit': page_size,
        'log': None,
    }

    for resp in session.filter_alphas(**kwargs):
        resp.raise_for_status()
        batch = resp.json().get('results') or []
        if not batch:
            break
        for alpha in batch:
            rows.append(normalize_alpha_row(alpha))
            if len(rows) >= max_alphas:
                return rows
        if len(batch) < page_size:
            break
        if request_delay > 0:
            time.sleep(request_delay)
    return rows


def fetch_submitted_alphas(
    session: AlphaFilterSession,
    *,
    start_date: str | None,
    end_date: str | None,
    regular_only: bool,
    page_size: int,
    max_alphas: int,
    request_delay: float,
) -> list[dict[str, Any]]:
    """Paginate OS submitted alphas (REGULAR + SUPER by default)."""
    if regular_only:
        return _fetch_one_type(
            session,
            start_date=start_date,
            end_date=end_date,
            alpha_type='REGULAR',
            page_size=page_size,
            max_alphas=max_alphas,
            request_delay=request_delay,
        )

    regular_rows = _fetch_one_type(
        session,
        start_date=start_date,
        end_date=end_date,
        alpha_type='REGULAR',
        page_size=page_size,
        max_alphas=max_alphas,
        request_delay=request_delay,
    )
    remaining = max(0, max_alphas - len(regular_rows))
    if remaining == 0:
        return regular_rows

    super_rows = _fetch_one_type(
        session,
        start_date=start_date,
        end_date=end_date,
        alpha_type='SUPER',
        page_size=page_size,
        max_alphas=remaining,
        request_delay=request_delay,
    )
    return regular_rows + super_rows


def _cell(count: int, super_count: int) -> dict[str, int]:
    return {'count': int(count), 'super_count': int(super_count)}


def aggregate_month_region(
    alphas: Iterable[dict[str, Any]],
    *,
    region_order: Sequence[str] | None = None,
) -> dict[str, Any]:
    """
    Aggregate alphas into month × region counts.

    Returns a JSON-ready dict with months, regions, pivot, rows, totals.
    """
    order = list(region_order or DEFAULT_REGION_ORDER)
    total: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    super_cnt: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    region_set: set[str] = set()
    skipped = 0

    for alpha in alphas:
        month = parse_submitted_month(alpha.get('dateSubmitted') or '')
        region = str(alpha.get('region') or 'UNKNOWN').strip().upper()
        if not month:
            skipped += 1
            continue
        total[month][region] += 1
        if alpha.get('type') == 'SUPER':
            super_cnt[month][region] += 1
        region_set.add(region)

    months = sorted(total.keys())
    known = [r for r in order if r in region_set]
    extra = sorted(region_set - set(known))
    regions = known + extra

    pivot: dict[str, dict[str, dict[str, int]]] = {}
    rows: list[dict[str, Any]] = []
    column_totals = {r: _cell(0, 0) for r in regions}
    grand = _cell(0, 0)

    for month in months:
        pivot[month] = {}
        row_total = _cell(0, 0)
        for region in regions:
            n = total.get(month, {}).get(region, 0)
            sa = super_cnt.get(month, {}).get(region, 0)
            if n:
                pivot[month][region] = _cell(n, sa)
                rows.append(
                    {
                        'month': month,
                        'region': region,
                        'count': n,
                        'super_count': sa,
                    }
                )
            row_total['count'] += n
            row_total['super_count'] += sa
            column_totals[region]['count'] += n
            column_totals[region]['super_count'] += sa
        if row_total['count']:
            pivot[month]['total'] = row_total
        grand['count'] += row_total['count']
        grand['super_count'] += row_total['super_count']

    return {
        'months': months,
        'regions': regions,
        'pivot': pivot,
        'rows': rows,
        'column_totals': column_totals,
        'grand_total': grand,
        'skipped': skipped,
    }


def _fmt_count(total: int, sa: int) -> str:
    """Cell text: total count; SA count in parentheses when > 0."""
    if total <= 0:
        return ''
    if sa > 0:
        return f'{total} ({sa})'
    return str(total)


def _pivot_to_legacy(result: dict[str, Any]) -> tuple[dict[str, dict[str, int]], dict[str, dict[str, int]]]:
    total: dict[str, dict[str, int]] = {}
    super_cnt: dict[str, dict[str, int]] = {}
    for month, row in (result.get('pivot') or {}).items():
        total[month] = {}
        super_cnt[month] = {}
        for region, cell in row.items():
            if region == 'total':
                continue
            total[month][region] = int(cell.get('count') or 0)
            super_cnt[month][region] = int(cell.get('super_count') or 0)
    return total, super_cnt


def format_pivot_table(result: dict[str, Any]) -> str:
    """Return kits-style pivot table text from monthly submit JSON output."""
    months = list(result.get('months') or [])
    regions = list(result.get('regions') or [])
    total, super_cnt = _pivot_to_legacy(result)
    if not months:
        return '无符合条件的提交记录。'

    col_w: dict[str, int] = {r: len(r) for r in regions}
    col_w['total'] = len('total')

    for month in months:
        for r in regions:
            cell = _fmt_count(total.get(month, {}).get(r, 0), super_cnt.get(month, {}).get(r, 0))
            col_w[r] = max(col_w[r], len(cell))
        row_total = sum(total.get(month, {}).get(r, 0) for r in regions)
        row_sa = sum(super_cnt.get(month, {}).get(r, 0) for r in regions)
        col_w['total'] = max(col_w['total'], len(_fmt_count(row_total, row_sa)))

    for r in regions:
        g_total = sum(total.get(m, {}).get(r, 0) for m in months)
        g_sa = sum(super_cnt.get(m, {}).get(r, 0) for m in months)
        col_w[r] = max(col_w[r], len(_fmt_count(g_total, g_sa)))
    grand_total = sum(sum(total.get(m, {}).values()) for m in months)
    grand_sa = sum(sum(super_cnt.get(m, {}).values()) for m in months)
    col_w['total'] = max(col_w['total'], len(_fmt_count(grand_total, grand_sa)))

    for r in regions:
        col_w[r] = max(col_w[r], len(r))

    header = f"{'month':<8}" + ' '.join(f'{r:>{col_w[r]}}' for r in regions) + f" {'total':>{col_w['total']}}"
    lines = [header, '-' * len(header)]

    grand_by_region: dict[str, int] = defaultdict(int)
    grand_sa_by_region: dict[str, int] = defaultdict(int)

    for month in months:
        row = total.get(month, {})
        sa_row = super_cnt.get(month, {})
        row_total = sum(row.get(r, 0) for r in regions)
        row_sa = sum(sa_row.get(r, 0) for r in regions)
        cells: list[str] = []
        for r in regions:
            n = row.get(r, 0)
            sa = sa_row.get(r, 0)
            grand_by_region[r] += n
            grand_sa_by_region[r] += sa
            cell = _fmt_count(n, sa)
            cells.append(f'{cell:>{col_w[r]}}' if cell else f"{'':>{col_w[r]}}")
        lines.append(
            f'{month:<8}' + ' '.join(cells) + f" {_fmt_count(row_total, row_sa):>{col_w['total']}}"
        )

    lines.append('-' * len(header))
    footer_cells = [
        f"{_fmt_count(grand_by_region[r], grand_sa_by_region[r]):>{col_w[r]}}" for r in regions
    ]
    lines.append(
        f"{'total':<8}" + ' '.join(footer_cells) + f" {_fmt_count(grand_total, grand_sa):>{col_w['total']}}"
    )
    return '\n'.join(lines)


def print_pivot_table(result: dict[str, Any]) -> None:
    """Print kits-style month × region pivot table."""
    print(format_pivot_table(result))


def print_monthly_submit_report(result: dict[str, Any]) -> None:
    """Print summary line + pivot table."""
    regular_n = int(result.get('regular_count') or 0)
    super_n = int(result.get('super_count') or 0)
    total_n = int(result.get('total_alphas') or 0)
    print(
        f'共获取 {total_n} 条已提交 alpha（REGULAR={regular_n}, SUPER={super_n}）'
    )
    print()
    print_pivot_table(result)
    print()
