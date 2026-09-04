#!/usr/bin/env python3
"""Offline tests for tools.expr (no HTTP)."""
from __future__ import annotations

import sys
from pathlib import Path

WQB_ROOT = Path(__file__).resolve().parents[1]
ROOT = WQB_ROOT.parent
if str(WQB_ROOT) not in sys.path:
    sys.path.insert(0, str(WQB_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.expr.api import (
    SlotKind,
    default_expression_analyze,
    default_expression_transform,
    default_expression_validate,
    is_exempt_field,
)


EXPR = (
    "st1 = ts_zscore(ts_backfill(star_val_dividend_projection_fy12, 60), 250);"
    "group_scale(st1, sector)"
)


def test_validate_offline():
    result = default_expression_validate.validate_expression(EXPR, check_fields=False)
    assert result.is_valid, result.errors


def test_analyze_counts():
    stats = default_expression_analyze.analyze_expression(EXPR)
    assert stats.unique_operator_count >= 3
    assert stats.unique_field_count == 1
    assert "star_val_dividend_projection_fy12" in stats.unique_fields
    assert is_exempt_field("sector")
    assert "sector" not in stats.unique_fields


def test_window_slots():
    slots = default_expression_transform.extract_window_slots(EXPR)
    kinds = {s.kind for s in slots}
    assert SlotKind.TS_WINDOW in kinds
    ts_slots = [s for s in slots if s.kind == SlotKind.TS_WINDOW]
    values = [s.value for s in ts_slots]
    assert 250 in values
    assert 60 not in values  # ts_backfill excluded
    slot_250 = next(s for s in ts_slots if s.value == 250)
    patched = default_expression_transform.apply_window_values(EXPR, {slot_250.slot_id: 120})
    assert "120" in patched


def test_validate_batch_offline():
    exprs = [
        EXPR,
        "rank(close)",
        "rank(!!!bad",
    ]
    results = default_expression_validate.validate_expression_batch(exprs, check_fields=False)
    assert len(results) == 3
    assert results[0].is_valid
    assert results[1].is_valid
    assert not results[2].is_valid
    assert results[2].index == 2

    payload = default_expression_validate.validate_expression_batch_json(
        exprs, check_fields=False
    )
    assert payload['total'] == 3
    assert payload['valid_count'] == 2
    assert payload['invalid_count'] == 1
    assert payload['results'][2]['errors']


if __name__ == "__main__":
    test_validate_offline()
    test_analyze_counts()
    test_window_slots()
    test_validate_batch_offline()
    print("ok")
