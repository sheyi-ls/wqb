"""Collect identifiers and prefetch fields before semantic analysis."""
from __future__ import annotations

from .parse import (
    AssignmentNode,
    ASTNode,
    BinaryOpNode,
    FunctionCallNode,
    IdentifierNode,
    ProgramNode,
    UnaryOpNode,
)

__all__ = ['collect_identifiers', 'collect_field_candidates']


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
