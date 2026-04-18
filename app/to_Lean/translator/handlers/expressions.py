import ast
from .. import constants
from .calls import handle_call

def handle_op(node, v):
    """演算子系のノード（BinOp, UnaryOp, BoolOp, Compare）を統合処理する"""
    if isinstance(node, ast.BinOp):
        l, r = v._wrap(node.left), v._wrap(node.right)
        if isinstance(node.op, ast.Div):
            return f"(py_div {l} {r})"
        op = constants.BIN_OPS.get(type(node.op))
        return f"({l} {op} {r})" if op else v._unsupported(node)

    if isinstance(node, ast.UnaryOp):
        op = constants.UNARY_OPS.get(type(node.op))
        return f"({op}{v._wrap(node.operand)})" if op else v._unsupported(node)

    if isinstance(node, ast.BoolOp):
        op = constants.BOOL_OPS.get(type(node.op), "??")
        return f"({(f' {op} ').join([v._wrap(val) for val in node.values])})"

    if isinstance(node, ast.Compare):
        parts = []
        curr_left = node.left
        for op_node, next_node in zip(node.ops, node.comparators):
            op = constants.COMP_OPS.get(type(op_node), "?")
            parts.append(f"({v._v(curr_left)} {op} {v._v(next_node)})")
            curr_left = next_node
        return parts[0] if len(parts) == 1 else f"({' && '.join(parts)})"

    return v._unsupported(node)

def handle_list_comp(node, v):
    """リスト内包表記を map/flatMap/filter/filterMap の組み合わせに変換する"""
    current_expr = v._v(node.elt)
    for i, gen in enumerate(reversed(node.generators)):
        target = v._v(gen.target)
        iterable = v._v(gen.iter)
        cond = " && ".join(f"({v._v(c)})" for c in gen.ifs) if gen.ifs else None
        is_innermost = (i == 0)
        if is_innermost:
            if cond:
                current_expr = f"({iterable}).filterMap (fun {target} => if {cond} then some ({current_expr}) else none)"
            else:
                current_expr = f"({iterable}).map (fun {target} => {current_expr})"
        else:
            if cond:
                current_expr = f"({iterable}).filter (fun {target} => {cond}).flatMap (fun {target} => {current_expr})"
            else:
                current_expr = f"({iterable}).flatMap (fun {target} => {current_expr})"
    return current_expr