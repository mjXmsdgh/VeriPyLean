import ast
from .. import constants
from .calls import handle_call

def handle_op(node, v):
    """演算子系のノード（BinOp, UnaryOp, BoolOp, Compare）を統合処理する"""
    # 二項演算 (a + b, a / b など) の処理
    if isinstance(node, ast.BinOp):
        l, r = v._wrap(node.left), v._wrap(node.right)
        # 除算は Lean 側で py_div として特殊扱い
        if isinstance(node.op, ast.Div):
            return v.emitter.format_binop(l, "/", r, is_div=True)
        # 定義された二項演算子マップから Lean 用のシンボルを取得
        op = constants.BIN_OPS.get(type(node.op))
        return v.emitter.format_binop(l, op, r) if op else v._unsupported(node)

    # 単項演算 (-a, not a など) の処理
    if isinstance(node, ast.UnaryOp):
        op = constants.UNARY_OPS.get(type(node.op))
        return v.emitter.format_unaryop(op, v._wrap(node.operand)) if op else v._unsupported(node)

    # 論理演算 (a and b, a or b) の処理
    if isinstance(node, ast.BoolOp):
        op = constants.BOOL_OPS.get(type(node.op), "??")
        # 複数の値を指定された演算子で結合
        return v.emitter.format_boolop(op, [v._wrap(val) for val in node.values])

    # 比較演算 (a < b < c など) の処理
    if isinstance(node, ast.Compare):
        parts = []
        curr_left = node.left
        # Python の連鎖比較 (a < b < c) を Lean の (a < b && b < c) 形式に分解
        for op_node, next_node in zip(node.ops, node.comparators):
            op = constants.COMP_OPS.get(type(op_node), "?")
            parts.append(f"({v._v(curr_left)} {op} {v._v(next_node)})")
            curr_left = next_node
        return v.emitter.format_compare(parts)

    return v._unsupported(node)

def handle_list_comp(node, v):
    """リスト内包表記を map/flatMap/filter/filterMap の組み合わせに変換する"""
    res = v._v(node.elt)
    for i, gen in enumerate(reversed(node.generators)):
        cond = " && ".join(f"({v._v(c)})" for c in gen.ifs) if gen.ifs else None
        res = v.emitter.format_list_comp_step(
            v._v(gen.iter), v._v(gen.target), res, cond, is_innermost=(i == 0)
        )
    return res