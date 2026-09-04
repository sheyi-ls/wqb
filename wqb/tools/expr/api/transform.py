"""Expression transform API protocols and types."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Sequence

__all__ = [
    'ExpressionTransformAPI',
    'SlotKind',
    'WindowSlot',
]

PathStep = tuple[str, int | str]


class SlotKind(str, Enum):
    TS_WINDOW = 'ts_window'


@dataclass(frozen=True)
class WindowSlot:
    kind: SlotKind
    slot_id: str
    path: tuple[PathStep, ...]
    operator: str
    param_name: str
    value: int

    def label(self) -> str:
        return f'{self.operator}.{self.param_name}'


class ExpressionTransformAPI(Protocol):
    """Extract and rewrite expression slots (v1: ts window literals)."""

    def extract_window_slots(self, expression: str) -> list[WindowSlot]: ...

    def apply_window_values(
        self,
        expression: str,
        assignments: dict[str, int],
        *,
        slots: Sequence[WindowSlot] | None = None,
    ) -> str: ...

    def program_to_expression(self, program) -> str: ...
