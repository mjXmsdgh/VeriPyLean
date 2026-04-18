import ast
import fractions
from .. import types
from . import constants

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

# --- Helper Functions for Handlers ---

def extract_doc_and_body(node):
    """ノードからdocstringを除去した本体ステートメントを返す"""
    doc = ast.get_docstring(node)
    stmts = node.body
    if doc and stmts and isinstance(stmts[0], ast.Expr):
        stmts = stmts[1:]
    return doc, stmts

def format_args(args_node, context):
    """関数引数を (name : Type) の形式で結合する"""
    return " ".join([f"({a.arg} : {types.translate_type(a.annotation, context)})" for a in args_node.args])

def get_block_lines(v, stmts, is_theorem=False):
    """複数のステートメントを変換し、行のリストとして返す"""
    if not stmts:
        return ["()" if not is_theorem else "True"]
    
    lines = []
    for i, stmt in enumerate(stmts):
        lines.append(v._v(stmt))
        if i == len(stmts) - 1:
            if isinstance(stmt, (ast.Assign, ast.Assert)):
                lines.append("()" if not is_theorem else "True")
    return lines

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

def handle_function_def(node, v):
    """関数・定理定義の変換をハンドリングする"""
    doc, stmts = extract_doc_and_body(node)
    args = format_args(node.args, v.context)
    is_thm = node.name.startswith(("verify_", "theorem_"))
    meta = v.context.functions.get(node.name, {})
    
    is_ret = is_thm and isinstance(stmts[-1], ast.Return)
    body_stmts = stmts[:-1] if is_ret else stmts
    
    if is_thm:
        prop = v._v(stmts[-1].value) if is_ret else "True"
        body_lines = get_block_lines(v, body_stmts, is_theorem=True)
        return v.emitter.format_theorem(node.name, args, prop, body_lines, doc=doc)
    else:
        ret_type = types.translate_type(node.returns, v.context)
        body_lines = get_block_lines(v, body_stmts, is_theorem=False)
        return v.emitter.format_function(
            node.name, args, ret_type, body_lines, 
            doc=doc, 
            termination_hint=meta.get("hint"),
            is_recursive=meta.get("is_recursive")
        )

def handle_class_def(node, v):
    """クラス定義（Enum/Structure）をハンドリングする"""
    kind = v.context.classes.get(node.name)
    if kind == "enum":
        variants = []
        for s in node.body:
            if isinstance(s, ast.Assign):
                for t in s.targets:
                    if isinstance(t, ast.Name):
                        variants.append(t.id)
        return v.emitter.format_inductive(node.name, variants)
    
    if kind == "structure":
        fields = []
        for s in node.body:
            if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name):
                fields.append((
                    s.target.id, 
                    types.translate_type(s.annotation, v.context)
                ))
        return v.emitter.format_structure(node.name, fields)
    
    return v._unsupported(node, "Only Enums and @dataclass are supported")

def handle_if(node, v):
    """If文の変換をハンドリングする"""
    then_lines = get_block_lines(v, node.body)
    else_lines = get_block_lines(v, node.orelse) if node.orelse else None
    return v.emitter.format_if_stmt(v._v(node.test), then_lines, else_lines)

def handle_call(node, v):
    """関数呼び出しの変換をハンドリングする（組み込みハンドラを含む）"""
    fn = v._v(node.func)
    h = BUILTIN_CALL_HANDLERS.get(fn) or (isinstance(node.func, ast.Attribute) and METHOD_CALL_HANDLERS.get(node.func.attr))
    if h:
        res = h(node, v)
        if res: return res
    args = [v._wrap(a, trigger_types=(ast.IfExp, ast.BinOp)) for a in node.args]
    return fn if not args else f"{fn} {' '.join(args)}"

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