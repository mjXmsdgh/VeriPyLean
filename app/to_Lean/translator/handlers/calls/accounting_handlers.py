import ast
import fractions

def _handle_decimal_call(node, visitor):
    """Decimal('0.1') などのリテラルを (1/10 : Rat) に変換する"""
    if len(node.args) == 1 and isinstance(node.args[0], ast.Constant):
        try:
            f = fractions.Fraction(node.args[0].value)
            return f"({f.numerator}/{f.denominator} : Rat)"
        except Exception: pass
    return None

def _handle_quantize_method(node, visitor):
    """Decimal.quantize メソッドの変換"""
    target = visitor._v(node.func.value)
    is_half_up = any(kw.arg == "rounding" and isinstance(kw.value, ast.Name) and kw.value.id == "ROUND_HALF_UP" for kw in node.keywords)
    return f"(py_round_half_up {target})" if is_half_up else None

HANDLERS = {
    "Decimal": _handle_decimal_call,
    "decimal.Decimal": _handle_decimal_call,
}

METHOD_HANDLERS = {"quantize": _handle_quantize_method}