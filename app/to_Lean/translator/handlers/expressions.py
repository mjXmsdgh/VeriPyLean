import ast
from .. import constants

OP_PRECEDENCE = {
    ast.Pow: 30,
    ast.Mult: 20,
    ast.Div: 20,
    ast.FloorDiv: 20,
    ast.Mod: 20,
    ast.Add: 10,
    ast.Sub: 10,
}

def _should_wrap_operand(parent_op, operand, is_right=False):
    """二項演算のオペランドに括弧が必要かどうかを判定する"""
    if isinstance(operand, (ast.IfExp, ast.BoolOp, ast.Compare)):
        return True
    if isinstance(operand, ast.BinOp):
        p_prec = OP_PRECEDENCE.get(type(parent_op), 0)
        c_prec = OP_PRECEDENCE.get(type(operand.op), 0)
        if c_prec < p_prec:
            return True
        if c_prec == p_prec:
            # 右結合の累乗 (a ** b) ** c
            if not is_right and isinstance(parent_op, ast.Pow):
                return True
            # 左結合の減算・除算の右オペランド: a - (b + c), a - (b - c), a / (b * c) など
            if is_right and isinstance(parent_op, (ast.Sub, ast.Div, ast.FloorDiv, ast.Mod)):
                return True
        return False
    return False

def _format_binop_operand(v, parent_op, operand, is_right=False):
    """二項演算のオペランドを文字列化し、必要なら括弧を付与する"""
    res = v._v(operand)
    if _should_wrap_operand(parent_op, operand, is_right=is_right):
        return f"({res})"
    return res

def handle_binop(node, v):
    """二項演算 (a + b, a / b) の処理"""
    l_raw, r_raw = node.left, node.right
    l_str = _format_binop_operand(v, node.op, l_raw, is_right=False)
    r_str = _format_binop_operand(v, node.op, r_raw, is_right=True)
    
    # 型キャストの挿入ロジック: 片方が Float(Rat) 定数の場合、もう片方を Rat にキャスト
    is_l_float = isinstance(l_raw, ast.Constant) and isinstance(l_raw.value, float)
    is_r_float = isinstance(r_raw, ast.Constant) and isinstance(r_raw.value, float)

    if is_l_float and not is_r_float:
        if not (r_str.startswith("(") and r_str.endswith(" : Rat)")):
            r_str = f"({r_str} : Rat)"
    elif is_r_float and not is_l_float:
        if not (l_str.startswith("(") and l_str.endswith(" : Rat)")):
            l_str = f"({l_str} : Rat)"

    is_div = isinstance(node.op, ast.Div)
    op = constants.BIN_OPS.get(type(node.op))
    if not op: return v._unsupported(node)

    if is_div:
        # py_div は関数適用なので、引数が複合式なら括弧で包む
        if isinstance(l_raw, (ast.BinOp, ast.IfExp, ast.BoolOp, ast.Compare, ast.Call)) and not (l_str.startswith("(") and l_str.endswith(")")):
            l_str = f"({l_str})"
        if isinstance(r_raw, (ast.BinOp, ast.IfExp, ast.BoolOp, ast.Compare, ast.Call)) and not (r_str.startswith("(") and r_str.endswith(")")):
            r_str = f"({r_str})"

    return v.emitter.format_binop(l_str, op, r_str, is_div=is_div)

def handle_unaryop(node, v):
    """単項演算 (-a, not a) の処理"""
    op = constants.UNARY_OPS.get(type(node.op))
    return v.emitter.format_unaryop(op, v._wrap(node.operand)) if op else v._unsupported(node)

def handle_boolop(node, v):
    """論理演算 (a and b) の処理"""
    op = constants.BOOL_OPS.get(type(node.op), "??")
    return v.emitter.format_boolop(op, [v._wrap(val) for val in node.values])

def handle_compare(node, v):
    """比較演算 (a < b < c) の処理"""
    ops = [constants.COMP_OPS.get(type(o), "?") for o in node.ops]
    vals = [node.left] + node.comparators
    # a < b < c を (a < b) && (b < c) の断片に分解
    parts = [f"({v._v(vals[i])} {ops[i]} {v._v(vals[i+1])})" for i in range(len(ops))]
    return v.emitter.format_compare(parts)

def handle_list_comp(node, v):
    """リスト内包表記を map/flatMap/filter/filterMap の組み合わせに変換する"""
    res = v._v(node.elt)
    for i, gen in enumerate(reversed(node.generators)):
        cond = " && ".join(f"({v._v(c)})" for c in gen.ifs) if gen.ifs else None
        res = v.emitter.format_list_comp_step(
            v._v(gen.iter), v._v(gen.target), res, cond, is_innermost=(i == 0)
        )
    return res