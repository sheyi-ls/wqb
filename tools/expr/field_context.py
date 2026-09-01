"""Field context for semantic validation (API lookup, no CSV)."""
from __future__ import annotations

from .builtin import builtin_field_type, is_exempt_field
from .field_resolver import FieldResolver
from .parse import OperatorSpec, OperatorSpecBuilder, ParamType

__all__ = ['FieldContext']


def _exempt_param_type(name: str) -> ParamType | None:
    type_name = builtin_field_type(name)
    if type_name is None:
        return None
    return ParamType[type_name]


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
