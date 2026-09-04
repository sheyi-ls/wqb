"""Default ``ExpressionTransformAPI`` implementation."""
from __future__ import annotations

import json
import math
from enum import Enum
from typing import Sequence

from ..api.transform import SlotKind, WindowSlot
from .core import parse_program
from .parse import (
    ASTNode,
    AssignmentNode,
    BinaryOpNode,
    BoolNode,
    FunctionCallNode,
    IdentifierNode,
    NanNode,
    NumberNode,
    OperatorSpecBuilder,
    ParamType,
    ProgramNode,
    StringNode,
    UnaryOpNode,
)

__all__ = [
    'DefaultExpressionTransform',
    'default_expression_transform',
]

PathStep = tuple[str, int | str]


class ParamRole(str, Enum):
    WINDOW_DAYS = 'WINDOW_DAYS'
    SKIP = 'SKIP'


_WINDOW_OPS_EXCLUDE = frozenset({'ts_backfill'})
_PARAM_ROLE_BLACKLIST: frozenset[tuple[str, str]] = frozenset(
    {
        ('ts_regression', 'lag'),
        ('ts_regression', 'rettype'),
        ('kth_element', 'k'),
        ('rank', 'rate'),
    }
)
_WINDOW_OPS_EXTRA = frozenset({'jump_decay', 'last_diff_value', 'kth_element', 'ts_step'})


def _build_param_role_map() -> dict[tuple[str, str], ParamRole]:
    roles: dict[tuple[str, str], ParamRole] = {}
    for op_name, spec in OperatorSpecBuilder.build_all_specs().items():
        if op_name in _WINDOW_OPS_EXCLUDE:
            continue
        is_ts = op_name.startswith('ts_') or op_name in _WINDOW_OPS_EXTRA
        if not is_ts:
            continue
        params = list(spec.positional_params) + list(spec.keyword_params.values())
        for ps in params:
            key = (op_name, ps.name)
            if key in _PARAM_ROLE_BLACKLIST:
                roles[key] = ParamRole.SKIP
                continue
            if ps.param_type != ParamType.INT:
                roles[key] = ParamRole.SKIP
                continue
            if ps.name in ('d', 'lookback'):
                roles[key] = ParamRole.WINDOW_DAYS
            elif op_name == 'ts_step' and ps.name == 'n':
                roles[key] = ParamRole.WINDOW_DAYS
    return roles


PARAM_ROLE_MAP = _build_param_role_map()


def param_role(operator: str, param_name: str) -> ParamRole:
    return PARAM_ROLE_MAP.get((operator, param_name), ParamRole.SKIP)


def _path_to_slot_id(path: tuple[PathStep, ...]) -> str:
    parts: list[str] = []
    for kind, key in path:
        if kind == 'stmt':
            parts.append(f'stmt{key}')
        elif kind == 'final':
            parts.append('final')
        elif kind == 'args':
            parts.append(f'a{key}')
        elif kind == 'kw':
            parts.append(f'k:{key}')
        elif kind == 'unary':
            parts.append('u0')
        elif kind == 'left':
            parts.append('L')
        elif kind == 'right':
            parts.append('R')
        else:
            parts.append(f'{kind}{key}')
    return '/'.join(parts)


def _literal_int(node: ASTNode) -> int | None:
    if not isinstance(node, NumberNode):
        return None
    v = node.value
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return int(v)
    if isinstance(v, float) and math.isfinite(v) and float(v).is_integer() and v > 0:
        return int(v)
    return None


def _bind_param_names(node: FunctionCallNode) -> list[tuple[str, ASTNode, str]]:
    spec = OperatorSpecBuilder.build_all_specs().get(node.name)
    if spec is None:
        return []
    bound: list[tuple[str, ASTNode, str]] = []
    for i, arg in enumerate(node.args):
        if i < len(spec.positional_params):
            bound.append((spec.positional_params[i].name, arg, 'pos'))
    for key, arg in node.kwargs.items():
        if key in spec.keyword_params:
            bound.append((key, arg, 'kw'))
    return bound


def _walk_collect_slots(
    node: ASTNode,
    path: tuple[PathStep, ...],
    out: list[WindowSlot],
) -> None:
    if isinstance(node, FunctionCallNode):
        for pname, arg, kind in _bind_param_names(node):
            if kind == 'pos':
                idx = node.args.index(arg)
                child_path: tuple[PathStep, ...] = path + (('args', idx),)
            else:
                child_path = path + (('kw', pname),)

            if param_role(node.name, pname) == ParamRole.WINDOW_DAYS:
                lit = _literal_int(arg)
                if lit is not None:
                    out.append(
                        WindowSlot(
                            kind=SlotKind.TS_WINDOW,
                            slot_id=_path_to_slot_id(child_path),
                            path=child_path,
                            operator=node.name,
                            param_name=pname,
                            value=lit,
                        )
                    )
            _walk_collect_slots(arg, child_path, out)
        return

    if isinstance(node, UnaryOpNode):
        _walk_collect_slots(node.operand, path + (('unary', 0),), out)
        return

    if isinstance(node, BinaryOpNode):
        _walk_collect_slots(node.left, path + (('left', 0),), out)
        _walk_collect_slots(node.right, path + (('right', 0),), out)
        return

    if isinstance(node, AssignmentNode):
        _walk_collect_slots(node.value, path, out)
        return


def _resolve_path(root: ProgramNode, path: tuple[PathStep, ...]) -> ASTNode:
    if not path:
        raise ValueError('empty path')
    if path[0][0] == 'stmt':
        idx = int(path[0][1])
        node: ASTNode = root.statements[idx].value
        rest = path[1:]
    elif path[0][0] == 'final':
        node = root.final_expr
        rest = path[1:]
    else:
        raise ValueError(f'invalid path root: {path[0]}')

    i = 0
    while i < len(rest):
        step = rest[i]
        kind, key = step
        if kind == 'args':
            if not isinstance(node, FunctionCallNode):
                raise ValueError(f'expected FunctionCallNode at {step}')
            node = node.args[int(key)]
        elif kind == 'kw':
            if not isinstance(node, FunctionCallNode):
                raise ValueError(f'expected FunctionCallNode at {step}')
            node = node.kwargs[str(key)]
        elif kind == 'unary':
            if not isinstance(node, UnaryOpNode):
                raise ValueError(f'expected UnaryOpNode at {step}')
            node = node.operand
        elif kind == 'left':
            if not isinstance(node, BinaryOpNode):
                raise ValueError(f'expected BinaryOpNode at {step}')
            node = node.left
        elif kind == 'right':
            if not isinstance(node, BinaryOpNode):
                raise ValueError(f'expected BinaryOpNode at {step}')
            node = node.right
        else:
            raise ValueError(f'unknown path step: {step}')
        i += 1
    return node


def ast_to_expression(node: ASTNode) -> str:
    if isinstance(node, NumberNode):
        v = node.value
        if isinstance(v, float) and math.isfinite(v) and float(v).is_integer():
            return str(int(v))
        return str(v)
    if isinstance(node, StringNode):
        return repr(node.value)
    if isinstance(node, BoolNode):
        return 'true' if node.value else 'false'
    if isinstance(node, NanNode):
        return 'nan'
    if isinstance(node, IdentifierNode):
        return node.name
    if isinstance(node, UnaryOpNode):
        op = node.op
        inner = ast_to_expression(node.operand)
        if op == 'not':
            return f'not {inner}'
        return f'{op}{inner}'
    if isinstance(node, FunctionCallNode):
        args_parts: list[str] = []
        for arg in node.args:
            args_parts.append(ast_to_expression(arg))
        for key, val in node.kwargs.items():
            args_parts.append(f'{key}={ast_to_expression(val)}')
        return f'{node.name}({", ".join(args_parts)})'
    if isinstance(node, BinaryOpNode):
        return f'{ast_to_expression(node.left)}{node.op}{ast_to_expression(node.right)}'
    if isinstance(node, AssignmentNode):
        return f'{node.var_name} = {ast_to_expression(node.value)}'
    raise TypeError(f'unsupported AST node: {type(node).__name__}')


DEFAULT_WINDOW_VALUES: tuple[int, ...] = (5, 10, 21, 63, 126, 252, 504)


def window_candidates_for_value(
    base_value: int,
    *,
    window_values: Sequence[int] | None = None,
) -> list[int]:
    _ = base_value
    cands = window_values if window_values else DEFAULT_WINDOW_VALUES
    return sorted({max(1, int(v)) for v in cands})


def slots_to_json(slots: Sequence[WindowSlot]) -> str:
    payload = [
        {
            'kind': s.kind.value,
            'slot_id': s.slot_id,
            'operator': s.operator,
            'param': s.param_name,
            'value': s.value,
            'label': s.label(),
        }
        for s in slots
    ]
    return json.dumps(payload, ensure_ascii=False)


class DefaultExpressionTransform:
    """Default implementation of ``ExpressionTransformAPI``."""

    def extract_window_slots(self, expression: str) -> list[WindowSlot]:
        program = parse_program(expression)
        slots: list[WindowSlot] = []
        for i, stmt in enumerate(program.statements):
            _walk_collect_slots(stmt, (('stmt', i),), slots)
        _walk_collect_slots(program.final_expr, (('final', 0),), slots)
        return slots

    def apply_window_values(
        self,
        expression: str,
        assignments: dict[str, int],
        *,
        slots: Sequence[WindowSlot] | None = None,
    ) -> str:
        program = parse_program(expression)
        slot_list = list(slots) if slots is not None else self.extract_window_slots(expression)
        by_id = {s.slot_id: s for s in slot_list}
        for slot_id, new_val in assignments.items():
            slot = by_id.get(slot_id)
            if slot is None:
                raise KeyError(f'unknown slot_id: {slot_id}')
            iv = int(new_val)
            if iv <= 0:
                raise ValueError(f'window must be positive: {slot_id}={iv}')
            target = _resolve_path(program, slot.path)
            if not isinstance(target, NumberNode):
                raise TypeError(f'slot {slot_id} does not point to NumberNode')
            target.value = float(iv) if isinstance(target.value, float) else iv
        return self.program_to_expression(program)

    def program_to_expression(self, program: ProgramNode) -> str:
        stmts = '; '.join(
            f'{s.var_name} = {ast_to_expression(s.value)}' for s in program.statements
        )
        tail = ast_to_expression(program.final_expr)
        return f'{stmts}; {tail}' if stmts else tail


default_expression_transform = DefaultExpressionTransform()
