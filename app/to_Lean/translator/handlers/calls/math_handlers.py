import ast

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

HANDLERS = {
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