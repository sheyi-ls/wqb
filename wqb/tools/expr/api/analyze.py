"""Expression analysis API protocols and types."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

__all__ = [
    'ExpressionAnalyzeAPI',
    'ExpressionStats',
]


@dataclass(frozen=True)
class ExpressionStats:
    operators: tuple[str, ...]
    fields: tuple[str, ...]
    operator_count: int
    field_count: int

    @property
    def unique_operators(self) -> frozenset[str]:
        return frozenset(self.operators)

    @property
    def unique_fields(self) -> frozenset[str]:
        return frozenset(self.fields)

    @property
    def unique_operator_count(self) -> int:
        return len(self.unique_operators)

    @property
    def unique_field_count(self) -> int:
        return len(self.unique_fields)


class ExpressionAnalyzeAPI(Protocol):
    """Operator and datafield usage statistics."""

    def analyze_expression(self, expression: str) -> ExpressionStats: ...

    def count_unique_operators(self, expression: str) -> int: ...

    def count_unique_fields(self, expression: str) -> int: ...
