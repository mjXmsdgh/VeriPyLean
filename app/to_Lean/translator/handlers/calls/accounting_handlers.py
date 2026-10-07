from __future__ import annotations

import ast
import fractions
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from ...core import LeanTranslator

def _handle_decimal_call(node: ast.Call, visitor: LeanTranslator) -> str | None:
    """Decimal('0.1') などのリテラルを (1/10 : Rat) に変換する"""
    if len(node.args) == 1 and isinstance(node.args[0], ast.Constant):
        val = node.args[0].value
        if isinstance(val, (str, int, float)):
            try:
                f = fractions.Fraction(val)
                return f"({f.numerator}/{f.denominator} : Rat)"
            except Exception: pass
    return None

def _handle_quantize_method(node: ast.Call, visitor: LeanTranslator) -> str | None:
    """Decimal.quantize メソッドの変換"""
    if not isinstance(node.func, ast.Attribute):
        return None
    target = visitor._v(node.func.value)
    is_half_up = any(kw.arg == "rounding" and isinstance(kw.value, ast.Name) and kw.value.id == "ROUND_HALF_UP" for kw in node.keywords)
    return f"(py_round_half_up {target})" if is_half_up else None

HANDLERS: dict[str, Callable[[ast.Call, LeanTranslator], str | None]] = {
    "Decimal": _handle_decimal_call,
    "decimal.Decimal": _handle_decimal_call,
}

METHOD_HANDLERS: dict[str, Callable[[ast.Call, LeanTranslator], str | None]] = {"quantize": _handle_quantize_method}