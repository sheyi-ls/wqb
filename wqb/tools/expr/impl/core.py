"""Internal builtins, identifier collection, and parse helpers."""
from __future__ import annotations

from typing import Any

from .parse import (
    AssignmentNode,
    ASTNode,
    BinaryOpNode,
    FunctionCallNode,
    IdentifierNode,
    Parser,
    ProgramNode,
    Tokenizer,
    UnaryOpNode,
)

__all__ = [
    'BUILTIN_DATAFIELDS',
    'builtin_field_info',
    'builtin_field_type',
    'collect_field_candidates',
    'collect_identifiers',
    'is_countable_field',
    'is_exempt_field',
    'normalize_field_id',
    'parse_program',
]

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


def parse_program(expression: str):
    text = str(expression or '').strip()
    if not text:
        raise ValueError('empty expression')
    tokens = Tokenizer(text).tokenize()
    return Parser(tokens).parse()


def collect_identifiers(node: ASTNode) -> set[str]:
    names: set[str] = set()

    def walk(n: ASTNode) -> None:
        if isinstance(n, IdentifierNode):
            names.add(n.name)
            return
        if isinstance(n, FunctionCallNode):
            for arg in n.args:
                walk(arg)
            for val in n.kwargs.values():
                walk(val)
            return
        if isinstance(n, UnaryOpNode):
            walk(n.operand)
            return
        if isinstance(n, BinaryOpNode):
            walk(n.left)
            walk(n.right)
            return
        if isinstance(n, AssignmentNode):
            walk(n.value)
            return

    walk(node)
    return names


def collect_field_candidates(program: ProgramNode) -> set[str]:
    """Identifiers excluding assignment LHS variable names."""
    defined = {stmt.var_name for stmt in program.statements}
    ids = collect_identifiers(program.final_expr)
    for stmt in program.statements:
        ids |= collect_identifiers(stmt.value)
    return {n for n in ids if n not in defined}
