import ast
from . import math_handlers, accounting_handlers, datetime_handlers

BUILTIN_CALL_HANDLERS = {
    **math_handlers.HANDLERS,
    **accounting_handlers.HANDLERS,
    **datetime_handlers.HANDLERS,
}

METHOD_CALL_HANDLERS = {
    **accounting_handlers.METHOD_HANDLERS,
}

def handle_call(node, v):
    """関数呼び出しの変換をハンドリングする（組み込みハンドラを含む）"""
    fn = v._v(node.func)
    h = BUILTIN_CALL_HANDLERS.get(fn) or (isinstance(node.func, ast.Attribute) and METHOD_CALL_HANDLERS.get(node.func.attr))
    if h:
        res = h(node, v)
        if res: return res
    args = [v._wrap(a, trigger_types=(ast.IfExp, ast.BinOp)) for a in node.args]
    return fn if not args else f"{fn} {' '.join(args)}"