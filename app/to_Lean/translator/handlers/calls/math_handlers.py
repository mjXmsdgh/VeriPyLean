from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from ...core import LeanTranslator

def _handle_unary_call(lean_func: str) -> Callable[[ast.Call, LeanTranslator], str | None]:
    """単一引数の関数呼び出しを変換する汎用ハンドラ"""
    return lambda node, visitor: f"({lean_func} {visitor._wrap(node.args[0])})" if len(node.args) == 1 else None

def _handle_min_max_call(node: ast.Call, visitor: LeanTranslator) -> str | None:
    """min/maxを2変数関数のネストに展開する"""
    func_name: str = visitor._v(node.func)
    if len(node.args) >= 2:
        args_str: list[str] = [visitor._wrap(arg) for arg in node.args]
        result: str = args_str[-1]
        for arg in reversed(args_str[:-1]):
            result = f"({func_name} {arg} {result})"
        return result
    return None

HANDLERS: dict[str, Callable[[ast.Call, LeanTranslator], str | None]] = {
    "math.ceil": _handle_unary_call("py_ceil"),
    "ceil": _handle_unary_call("py_ceil"),
    "math.floor": _handle_unary_call("py_floor"),
    "floor": _handle_unary_call("py_floor"),
    "round": _handle_unary_call("py_round"),
    "sum": _handle_unary_call("py_sum"),
    "len": _handle_unary_call("List.length"),
    "min": _handle_min_max_call,
    "max": _handle_min_max_call,
}