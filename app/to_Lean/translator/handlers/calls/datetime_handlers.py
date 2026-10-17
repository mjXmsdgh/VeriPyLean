from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from ...core import LeanTranslator

def _handle_date_call(node: ast.Call, visitor: LeanTranslator) -> str | None:
    """date(y, m, d) を Date 構造体リテラルに変換する"""
    if len(node.args) == 3:
        a: list[str] = [visitor._v(arg) for arg in node.args]
        return f"({{ year := {a[0]}, month := {a[1]}, day := {a[2]} }} : Date)"
    return None

HANDLERS: dict[str, Callable[[ast.Call, LeanTranslator], str | None]] = {
    "date": _handle_date_call,
    "datetime.date": _handle_date_call,
}