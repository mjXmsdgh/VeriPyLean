import ast

# 組み込み関数の特殊ハンドラ
BUILTIN_CALL_HANDLERS = {
    "sum": lambda n, v: f"py_sum {v._v(n.args[0])}",
    "len": lambda n, v: f"({v._v(n.args[0])}).length",
}

# メソッド呼び出しの特殊ハンドラ
METHOD_CALL_HANDLERS = {
    "append": lambda n, v: f"{v._v(n.func.value)} ++ [{v._v(n.args[0])}]",
}

def handle_call(node, v):
    """関数呼び出しをLeanの適用形式 (f x y) に変換する"""
    fn = v._v(node.func)
    # 特殊なハンドラがあるか確認
    h = BUILTIN_CALL_HANDLERS.get(fn) or \
        (isinstance(node.func, ast.Attribute) and METHOD_CALL_HANDLERS.get(node.func.attr))
    
    if h:
        res = h(node, v)
        if res: return res
    
    args = [v._wrap(a, trigger_types=(ast.IfExp, ast.BinOp)) for a in node.args]
    return fn if not args else f"{fn} {' '.join(args)}"