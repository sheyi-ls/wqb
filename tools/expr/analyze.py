"""Operator and datafield usage statistics from AST."""
from __future__ import annotations

from dataclasses import dataclass

from .builtin import is_countable_field
from .parse import (
    AssignmentNode,
    ASTNode,
    BinaryOpNode,
    FunctionCallNode,
    IdentifierNode,
    OperatorSpecBuilder,
    ProgramNode,
    UnaryOpNode,
)
from .validate import parse_program

__all__ = [
    'ExpressionStats',
    'analyze_expression',
    'count_unique_operators',
    'count_unique_fields',
]

_OPERATOR_NAMES = frozenset(OperatorSpecBuilder.build_all_specs().keys())
_OPERATOR_LOWER = frozenset(n.lower() for n in _OPERATOR_NAMES)


def _is_operator_name(name: str) -> bool:
    return name.lower() in _OPERATOR_LOWER


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


def _analyze_program(program: ProgramNode) -> ExpressionStats:
    defined = {stmt.var_name for stmt in program.statements}
    operators: list[str] = []
    fields: list[str] = []

    def walk(node: ASTNode) -> None:
        if isinstance(node, FunctionCallNode):
            operators.append(node.name.lower())
            for arg in node.args:
                walk(arg)
            for val in node.kwargs.values():
                walk(val)
            return
        if isinstance(node, IdentifierNode):
            name = node.name
            if name in defined or _is_operator_name(name) or not is_countable_field(name):
                return
            fields.append(name.lower())
            return
        if isinstance(node, UnaryOpNode):
            walk(node.operand)
            return
        if isinstance(node, BinaryOpNode):
            walk(node.left)
            walk(node.right)
            return
        if isinstance(node, AssignmentNode):
            walk(node.value)
            return

    for stmt in program.statements:
        walk(stmt)
    walk(program.final_expr)

    return ExpressionStats(
        operators=tuple(operators),
        fields=tuple(fields),
        operator_count=len(operators),
        field_count=len(fields),
    )


def analyze_expression(expression: str) -> ExpressionStats:
    return _analyze_program(parse_program(expression))


def count_unique_operators(expression: str) -> int:
    return analyze_expression(expression).unique_operator_count


def count_unique_fields(expression: str) -> int:
    return analyze_expression(expression).unique_field_count
