"""
FASTEXPR tools: validate, analyze, transform.

Field validation uses wqb ``locate_field`` (no CSV). Built-in fields are exempt.
"""
from __future__ import annotations

from .analyze import (
    ExpressionStats,
    analyze_expression,
    count_unique_fields,
    count_unique_operators,
)
from .builtin import BUILTIN_DATAFIELDS, is_exempt_field
from .field_context import FieldContext
from .field_resolver import BrainFieldSession, FieldResolver
from .validate import (
    ValidationResult,
    parse_program,
    validate_expression,
    validate_expression_batch,
    validate_expression_batch_json,
    validation_result_to_dict,
)
from .transform.ts_window import (
    WindowSlot,
    apply_window_values,
    extract_window_slots,
    program_to_expression,
)

__all__ = [
    'BUILTIN_DATAFIELDS',
    'BrainFieldSession',
    'ExpressionStats',
    'FieldContext',
    'FieldResolver',
    'ValidationResult',
    'WindowSlot',
    'analyze_expression',
    'apply_window_values',
    'count_unique_fields',
    'count_unique_operators',
    'extract_window_slots',
    'is_exempt_field',
    'parse_program',
    'program_to_expression',
    'validate_expression',
    'validate_expression_batch',
    'validate_expression_batch_json',
    'validation_result_to_dict',
]
