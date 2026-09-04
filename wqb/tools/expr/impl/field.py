"""Field lookup and semantic-analysis context."""
from __future__ import annotations

from typing import Any

from ..api.validate import BrainFieldSession
from .core import (
    builtin_field_info,
    builtin_field_type,
    is_exempt_field,
    normalize_field_id,
)
from .parse import OperatorSpec, OperatorSpecBuilder, ParamType

__all__ = ['FieldContext', 'FieldResolver']


def _param_type_from_brain(type_str: str | None) -> ParamType | None:
    if not type_str:
        return None
    key = str(type_str).strip().upper()
    try:
        return ParamType[key]
    except KeyError:
        return None


def _exempt_param_type(name: str) -> ParamType | None:
    type_name = builtin_field_type(name)
    if type_name is None:
        return None
    return ParamType[type_name]


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


class FieldContext:
    """Drop-in replacement for ``DataContext`` using ``FieldResolver``."""

    def __init__(
        self,
        resolver: FieldResolver | None = None,
        *,
        check_fields: bool = True,
    ) -> None:
        self.check_fields = check_fields
        self.resolver = resolver or FieldResolver()
        self.operators = OperatorSpecBuilder.build_all_specs()

    def is_datafield(self, name: str) -> bool:
        if is_exempt_field(name):
            return True
        if not self.check_fields:
            return False
        return self.resolver.is_known_field(name)

    def get_datafield_type(self, name: str) -> ParamType | None:
        exempt = _exempt_param_type(name)
        if exempt is not None:
            return exempt
        if not self.check_fields:
            return None
        return self.resolver.resolve_type(name)

    def is_operator(self, name: str) -> bool:
        name_lower = name.lower()
        return any(op.lower() == name_lower for op in self.operators)

    def get_operator_spec(self, name: str) -> OperatorSpec | None:
        name_lower = name.lower()
        for op_name, op_spec in self.operators.items():
            if op_name.lower() == name_lower:
                return op_spec
        return None
