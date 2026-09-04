"""Default ``ExpressionAnalyzeAPI`` implementation."""
from __future__ import annotations

from ..api.analyze import ExpressionStats
from .core import is_countable_field, parse_program
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

__all__ = [
    'DefaultExpressionAnalyze',
    'default_expression_analyze',
]

_OPERATOR_NAMES = frozenset(OperatorSpecBuilder.build_all_specs().keys())
_OPERATOR_LOWER = frozenset(n.lower() for n in _OPERATOR_NAMES)


def _is_operator_name(name: str) -> bool:
    return name.lower() in _OPERATOR_LOWER


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


class DefaultExpressionAnalyze:
    """Default implementation of ``ExpressionAnalyzeAPI``."""

    def analyze_expression(self, expression: str) -> ExpressionStats:
        return _analyze_program(parse_program(expression))

    def count_unique_operators(self, expression: str) -> int:
        return self.analyze_expression(expression).unique_operator_count

    def count_unique_fields(self, expression: str) -> int:
        return self.analyze_expression(expression).unique_field_count


default_expression_analyze = DefaultExpressionAnalyze()
