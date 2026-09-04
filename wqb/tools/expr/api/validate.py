"""Expression validation API protocols and types."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Protocol

__all__ = [
    'BrainFieldSession',
    'ExpressionValidateAPI',
    'ValidationResult',
    'validation_result_to_dict',
]


class BrainFieldSession(Protocol):
    """BRAIN client with ``locate_field`` (e.g. ``WQBSession``)."""

    def locate_field(self, field_id: str, *args, **kwargs) -> Any: ...


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    errors: tuple[str, ...]
    expression: str
    index: int | None = None


def validation_result_to_dict(result: ValidationResult) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'expression': result.expression,
        'is_valid': result.is_valid,
        'errors': list(result.errors),
    }
    if result.index is not None:
        payload['index'] = result.index
    return payload


class ExpressionValidateAPI(Protocol):
    """Syntax + semantic validation of FASTEXPR alphas."""

    def validate_expression(
        self,
        expression: str,
        *,
        session: BrainFieldSession | None = None,
        check_fields: bool = True,
        resolver: Any | None = None,
    ) -> ValidationResult: ...

    def validate_expression_batch(
        self,
        expressions: Iterable[str],
        *,
        session: BrainFieldSession | None = None,
        check_fields: bool = True,
        resolver: Any | None = None,
    ) -> list[ValidationResult]: ...

    def validate_expression_batch_json(
        self,
        expressions: Iterable[str],
        *,
        session: BrainFieldSession | None = None,
        check_fields: bool = True,
        resolver: Any | None = None,
    ) -> dict[str, Any]: ...
