"""Resolve datafield types via wqb ``locate_field`` (no CSV)."""
from __future__ import annotations

from typing import Any, Protocol

from .builtin import (
    builtin_field_info,
    builtin_field_type,
    is_exempt_field,
    normalize_field_id,
)
from .parse import ParamType

__all__ = ['FieldResolver', 'BrainFieldSession']


class BrainFieldSession(Protocol):
    def locate_field(self, field_id: str, *args, **kwargs) -> Any: ...


def _param_type_from_brain(type_str: str | None) -> ParamType | None:
    if not type_str:
        return None
    key = str(type_str).strip().upper()
    try:
        return ParamType[key]
    except KeyError:
        return None


class FieldResolver:
    """Cache-backed field lookup: exempt list locally, others via ``locate_field``."""

    def __init__(self, session: BrainFieldSession | None = None) -> None:
        self.session = session
        self._cache: dict[str, ParamType | None] = {}

    def resolve_type(self, field_id: str) -> ParamType | None:
        name = normalize_field_id(field_id)
        if not name:
            return None

        key = name.lower()
        if key in self._cache:
            return self._cache[key]

        if is_exempt_field(name):
            pt = _param_type_from_brain(builtin_field_type(name))
            self._cache[key] = pt
            return pt

        if self.session is None:
            self._cache[key] = None
            return None

        resp = self.session.locate_field(name, log=None)
        if resp.status_code == 404:
            self._cache[key] = None
            return None
        resp.raise_for_status()
        body = resp.json()
        pt = _param_type_from_brain(body.get('type'))
        self._cache[key] = pt
        return pt

    def is_known_field(self, field_id: str) -> bool:
        return self.resolve_type(field_id) is not None

    def prefetch(self, field_ids: set[str] | list[str]) -> None:
        for fid in field_ids:
            self.resolve_type(fid)

    def field_info(self, field_id: str) -> dict[str, Any] | None:
        name = normalize_field_id(field_id)
        if not name:
            return None
        if is_exempt_field(name):
            return builtin_field_info(name)
        if self.session is None:
            return None
        resp = self.session.locate_field(name, log=None)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
