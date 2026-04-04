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

def _handle_unary_call(lean_func):
    """単一引数の関数呼び出しを変換する汎用ハンドラ"""
    return lambda node, visitor: f"({lean_func} {visitor._v(node.args[0])})" if len(node.args) == 1 else None

def _handle_min_max_call(node, visitor):
    """min/maxを2変数関数のネストに展開する"""
    func_name = visitor._v(node.func)
    if len(node.args) >= 2:
        args_str = [visitor._v(arg) for arg in node.args]
        result = args_str[-1]
        for arg in reversed(args_str[:-1]):
            result = f"({func_name} {arg} {result})"
        return result
    return None

def _handle_date_call(node, visitor):
    """date(y, m, d) を Date 構造体リテラルに変換する"""
    if len(node.args) == 3:
        a = [visitor._v(arg) for arg in node.args]
        return f"({{ year := {a[0]}, month := {a[1]}, day := {a[2]} }} : Date)"
    return None

def _handle_quantize_method(node, visitor):
    """Decimal.quantize メソッドの変換"""
    target = visitor._v(node.func.value)
    is_half_up = any(kw.arg == "rounding" and isinstance(kw.value, ast.Name) and kw.value.id == "ROUND_HALF_UP" for kw in node.keywords)
    return f"(py_round_half_up {target})" if is_half_up else None

BUILTIN_CALL_HANDLERS = {
    "Decimal": _handle_decimal_call, "decimal.Decimal": _handle_decimal_call,
    "math.ceil": _handle_unary_call("py_ceil"), "ceil": _handle_unary_call("py_ceil"),
    "math.floor": _handle_unary_call("py_floor"), "floor": _handle_unary_call("py_floor"),
    "round": _handle_unary_call("py_round"),
    "sum": _handle_unary_call("py_sum"),
    "len": _handle_unary_call("List.length"),
    "min": _handle_min_max_call, "max": _handle_min_max_call,
    "date": _handle_date_call, "datetime.date": _handle_date_call,
}

METHOD_CALL_HANDLERS = {
    "quantize": _handle_quantize_method,
}