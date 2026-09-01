"""Pluggable expression slot extractors (v1: ts window literals)."""
from __future__ import annotations

from enum import Enum

__all__ = ['SlotKind']


class SlotKind(str, Enum):
    TS_WINDOW = 'ts_window'
