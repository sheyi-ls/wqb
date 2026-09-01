#!/usr/bin/env python3
"""Offline tests for tools.analysis.monthly_submit_by_region."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from unittest.mock import Mock

WQB_ROOT = Path(__file__).resolve().parents[1]
ROOT = WQB_ROOT.parent
if str(WQB_ROOT) not in sys.path:
    sys.path.insert(0, str(WQB_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.analysis import aggregate_month_region, monthly_submit_count_by_region_json
from tools.analysis.monthly_submit_by_region import _normalize_alpha_row as _normalize_row


def _alpha(aid: str, region: str, month: str, kind: str = 'REGULAR'):
    return {
        'id': aid,
        'type': kind,
        'dateSubmitted': f'{month}-15T12:00:00Z',
        'settings': {'region': region},
    }


def test_aggregate_month_region():
    alphas = [
        _normalize_row(_alpha('a1', 'USA', '2025-12')),
        _normalize_row(_alpha('a2', 'USA', '2025-12', 'SUPER')),
        _normalize_row(_alpha('a3', 'EUR', '2026-01')),
    ]
    out = aggregate_month_region(alphas)
    assert out['months'] == ['2025-12', '2026-01']
    assert out['regions'] == ['USA', 'EUR']
    assert out['pivot']['2025-12']['USA']['count'] == 2
    assert out['pivot']['2025-12']['USA']['super_count'] == 1
    assert out['grand_total']['count'] == 3
    json.dumps(out)


class _MockSession:
    def __init__(self, batches: dict[str, list[list[dict]]]):
        self._batches = batches
        self._calls: dict[str, int] = defaultdict(int)

    def filter_alphas(self, **kwargs):
        alpha_type = kwargs.get('type')
        idx = self._calls[alpha_type]
        self._calls[alpha_type] += 1
        batch = self._batches[alpha_type][idx] if idx < len(self._batches[alpha_type]) else []
        resp = Mock()
        resp.raise_for_status = Mock()
        resp.json.return_value = {'results': batch}
        yield resp


def test_monthly_submit_count_by_region_json():
    session = _MockSession(
        {
            'REGULAR': [[_alpha('r1', 'USA', '2025-12'), _alpha('r2', 'EUR', '2025-12')]],
            'SUPER': [[_alpha('s1', 'USA', '2025-12', 'SUPER')]],
        }
    )
    out = monthly_submit_count_by_region_json(
        session,
        start_date='2025-12-01',
        request_delay=0,
    )
    assert out['total_alphas'] == 3
    assert out['regular_count'] == 2
    assert out['super_count'] == 1
    assert out['pivot']['2025-12']['USA']['count'] == 2
    json.dumps(out)


if __name__ == '__main__':
    test_aggregate_month_region()
    test_monthly_submit_count_by_region_json()
    print('ok')
