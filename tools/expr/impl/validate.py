"""Default ``ExpressionValidateAPI`` implementation."""
from __future__ import annotations

from typing import Any, Iterable

from ..api.validate import (
    BrainFieldSession,
    ValidationResult,
    validation_result_to_dict,
)
from .core import collect_field_candidates, parse_program
from .field import FieldContext, FieldResolver
from .parse import SemanticAnalyzer

__all__ = [
    'DefaultExpressionValidate',
    'default_expression_validate',
]


def _parse_program_safe(expression: str) -> tuple[Any | None, tuple[str, ...]]:
    try:
        return parse_program(expression), ()
    except SyntaxError as exc:
        return None, (f'Syntax error: {exc}',)
    except ValueError as exc:
        return None, (str(exc),)
    except Exception as exc:
        return None, (f'Validation error: {exc}',)


def _validate_parsed(
    expression: str,
    program,
    *,
    context: FieldContext,
    index: int | None = None,
) -> ValidationResult:
    analyzer = SemanticAnalyzer(context)
    is_valid, errors = analyzer.analyze(program)
    return ValidationResult(
        is_valid=is_valid,
        errors=tuple(errors),
        expression=expression,
        index=index,
    )


class DefaultExpressionValidate:
    """Default implementation of ``ExpressionValidateAPI``."""

    def validate_expression(
        self,
        expression: str,
        *,
        session: BrainFieldSession | None = None,
        check_fields: bool = True,
        resolver: FieldResolver | None = None,
    ) -> ValidationResult:
        """
        Validate a FASTEXPR alpha expression.

        When ``check_fields=True`` (default), every identifier that is not a local
        variable or operator must resolve as a datafield: built-in exempt list first,
        otherwise ``session.locate_field(id)``. ``region/universe/delay`` are not
        required. Pass ``check_fields=False`` for syntax/operator-only validation.
        """
        if check_fields and session is None and resolver is None:
            raise ValueError(
                'check_fields=True requires session (wqb WQBSession) or a FieldResolver'
            )

        program, parse_errors = _parse_program_safe(expression)
        if program is None:
            return ValidationResult(
                is_valid=False,
                errors=parse_errors,
                expression=str(expression),
            )

        field_resolver = resolver or FieldResolver(session)
        context = FieldContext(field_resolver, check_fields=check_fields)

        if check_fields:
            field_resolver.prefetch(collect_field_candidates(program))

        return _validate_parsed(expression, program, context=context)

    def validate_expression_batch(
        self,
        expressions: Iterable[str],
        *,
        session: BrainFieldSession | None = None,
        check_fields: bool = True,
        resolver: FieldResolver | None = None,
    ) -> list[ValidationResult]:
        """
        Batch validate expressions sharing one field cache / resolver.

        Parse/semantic errors are captured per item instead of aborting the batch.
        When ``check_fields=True``, all field candidates are prefetched once.
        """
        if check_fields and session is None and resolver is None:
            raise ValueError(
                'check_fields=True requires session (wqb WQBSession) or a FieldResolver'
            )

        expr_list = [str(e) for e in expressions]
        field_resolver = resolver or FieldResolver(session)
        context = FieldContext(field_resolver, check_fields=check_fields)

        parsed_items: list[tuple[str, Any | None, tuple[str, ...]]] = []
        all_candidates: set[str] = set()

        for expr in expr_list:
            program, parse_errors = _parse_program_safe(expr)
            parsed_items.append((expr, program, parse_errors))
            if program is not None and check_fields:
                all_candidates |= collect_field_candidates(program)

        if check_fields and all_candidates:
            field_resolver.prefetch(all_candidates)

        results: list[ValidationResult] = []
        for index, (expr, program, parse_errors) in enumerate(parsed_items):
            if program is None:
                results.append(
                    ValidationResult(
                        is_valid=False,
                        errors=parse_errors,
                        expression=expr,
                        index=index,
                    )
                )
                continue
            results.append(
                _validate_parsed(expr, program, context=context, index=index)
            )
        return results

    def validate_expression_batch_json(
        self,
        expressions: Iterable[str],
        *,
        session: BrainFieldSession | None = None,
        check_fields: bool = True,
        resolver: FieldResolver | None = None,
    ) -> dict[str, Any]:
        """Batch validate and return JSON-ready summary + per-item results."""
        results = self.validate_expression_batch(
            expressions,
            session=session,
            check_fields=check_fields,
            resolver=resolver,
        )
        valid_count = sum(1 for item in results if item.is_valid)
        return {
            'total': len(results),
            'valid_count': valid_count,
            'invalid_count': len(results) - valid_count,
            'check_fields': check_fields,
            'results': [validation_result_to_dict(item) for item in results],
        }


default_expression_validate = DefaultExpressionValidate()
