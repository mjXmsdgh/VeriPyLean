import ast
from .. import constants
from .calls import handle_call

def handle_binop(node, v):
    """二項演算 (a + b, a / b) の処理"""
    l, r = v._wrap(node.left), v._wrap(node.right)
    is_div = isinstance(node.op, ast.Div)
    op = "/" if is_div else constants.BIN_OPS.get(type(node.op))
    if not op: return v._unsupported(node)
    return v.emitter.format_binop(l, op, r, is_div=is_div)

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