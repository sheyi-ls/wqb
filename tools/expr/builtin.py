"""Built-in BRAIN datafields exempt from platform field lookup."""
from __future__ import annotations

from typing import Any

__all__ = ['BUILTIN_DATAFIELDS', 'builtin_field_type', 'is_exempt_field', 'is_countable_field', 'normalize_field_id']

BUILTIN_DATAFIELDS: dict[str, dict[str, str]] = {
    'returns': {
        'type': 'MATRIX',
        'description': 'Daily stock returns (BRAIN built-in).',
    },
    'close': {
        'type': 'MATRIX',
        'description': 'Daily close price (BRAIN built-in).',
    },
    'open': {
        'type': 'MATRIX',
        'description': 'Daily open price (BRAIN built-in).',
    },
    'high': {
        'type': 'MATRIX',
        'description': 'Daily high price (BRAIN built-in).',
    },
    'low': {
        'type': 'MATRIX',
        'description': 'Daily low price (BRAIN built-in).',
    },
    'volume': {
        'type': 'MATRIX',
        'description': 'Daily volume (BRAIN built-in).',
    },
    'vwap': {
        'type': 'MATRIX',
        'description': 'Volume weighted average price (BRAIN built-in).',
    },
    'cap': {
        'type': 'MATRIX',
        'description': 'Market capitalization (BRAIN built-in).',
    },
    'sector': {
        'type': 'GROUP',
        'description': 'Sector grouping (BRAIN built-in).',
    },
    'industry': {
        'type': 'GROUP',
        'description': 'Industry grouping (BRAIN built-in).',
    },
    'subindustry': {
        'type': 'GROUP',
        'description': 'Sub-industry grouping (BRAIN built-in).',
    },
    'market': {
        'type': 'GROUP',
        'description': 'Market grouping (BRAIN built-in).',
    },
    'exchange': {
        'type': 'GROUP',
        'description': 'Exchange grouping (BRAIN built-in).',
    },
    'country': {
        'type': 'GROUP',
        'description': 'Country grouping (BRAIN built-in).',
    },
}

_BUILTIN_LOWER = {k.lower(): k for k in BUILTIN_DATAFIELDS}


def normalize_field_id(name: str) -> str:
    return str(name or '').strip()


def is_exempt_field(name: str) -> bool:
    """True if *name* is on the no-lookup exemption list (built-in fields)."""
    return normalize_field_id(name).lower() in _BUILTIN_LOWER


def is_countable_field(name: str) -> bool:
    """True if *name* should appear in dataset unique-field counts (non-exempt)."""
    return not is_exempt_field(name)


def builtin_field_type(name: str) -> str | None:
    key = normalize_field_id(name).lower()
    canonical = _BUILTIN_LOWER.get(key)
    if canonical is None:
        return None
    return BUILTIN_DATAFIELDS[canonical]['type']


def builtin_field_info(name: str) -> dict[str, Any] | None:
    key = normalize_field_id(name).lower()
    canonical = _BUILTIN_LOWER.get(key)
    if canonical is None:
        return None
    return dict(BUILTIN_DATAFIELDS[canonical])
