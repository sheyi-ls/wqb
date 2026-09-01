#!/usr/bin/env python3
"""Offline tests for tools.correlation.pnl_matrix (mock session, no HTTP)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import Mock

WQB_ROOT = Path(__file__).resolve().parents[1]
ROOT = WQB_ROOT.parent
if str(WQB_ROOT) not in sys.path:
    sys.path.insert(0, str(WQB_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.correlation import pnl_corr_matrix, pnl_corr_matrix_json


def _pnl_payload(records):
    return {
        'schema': {
            'properties': [
                {'name': 'date'},
                {'name': 'pnl'},
            ]
        },
        'records': records,
    }


class _MockSession:
    def __init__(self, payloads: dict[str, dict]):
        self._payloads = payloads

    def get_pnl(self, alpha_id: str, *args, log=None, **kwargs):
        resp = Mock()
        resp.json.return_value = self._payloads[alpha_id]
        resp.raise_for_status = Mock()
        return resp


def _make_session():
    dates = [f'2024-01-{d:02d}' for d in range(1, 11)]
    rets_a = [1.0, -0.5, 2.0, -1.0, 0.5, 1.5, -0.8, 0.3, 1.2, -0.4]
    rets_b = [2.0, -1.0, 4.0, -2.0, 1.0, 3.0, -1.6, 0.6, 2.4, -0.8]
    cum_a, cum_b = 100.0, 200.0
    rec_a, rec_b = [], []
    for d, ra, rb in zip(dates, rets_a, rets_b):
        cum_a += ra
        cum_b += rb
        rec_a.append([d, cum_a])
        rec_b.append([d, cum_b])
    return _MockSession(
        {
            'A1': _pnl_payload(rec_a),
            'A2': _pnl_payload(rec_b),
            'BAD': _pnl_payload([]),
        }
    )


def test_pnl_corr_matrix_json():
    session = _make_session()
    out = pnl_corr_matrix_json(session, ['A1', 'A2', 'BAD'], years=0)
    assert out['alpha_ids'] == ['A1', 'A2']
    assert out['skipped'] == ['BAD']
    assert out['observations'] >= 2
    assert abs(out['matrix']['A1']['A2'] - 1.0) < 1e-6
    json.dumps(out)  # serializable


def test_pnl_corr_matrix_dataframe():
    session = _make_session()
    corr_df, skipped, obs = pnl_corr_matrix(session, ['A1', 'A2'], years=0)
    assert skipped == []
    assert obs >= 2
    assert abs(float(corr_df.loc['A1', 'A2']) - 1.0) < 1e-6


if __name__ == '__main__':
    test_pnl_corr_matrix_json()
    test_pnl_corr_matrix_dataframe()
    print('ok')
