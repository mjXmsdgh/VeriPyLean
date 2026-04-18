import ast
from . import constants, types

class BaseHandler:
    """名前や定数などの基本要素のハンドラ"""
    @staticmethod
    def get_handlers(v):
        return {
            ast.Constant: lambda n: v.emitter.format_constant(n.value),
            ast.Name: lambda n: n.id,
            ast.Attribute: lambda n: v.emitter.format_attribute(v._v(n.value), n.attr),
            ast.Pass: lambda _: "()",
        }

class ExpressionHandler:
    """式（演算、関数呼び出し、内包表記など）のハンドラ"""
    @staticmethod
    def get_handlers(v):
        return {
            ast.BinOp: lambda n: ExpressionHandler.handle_op(v, n),
            ast.UnaryOp: lambda n: ExpressionHandler.handle_op(v, n),
            ast.BoolOp: lambda n: ExpressionHandler.handle_op(v, n),
            ast.Compare: lambda n: ExpressionHandler.handle_op(v, n),
            ast.IfExp: lambda n: v.emitter.format_if_exp(v._v(n.test), v._v(n.body), v._v(n.orelse)),
            ast.List: lambda n: v.emitter.format_collection([v._v(e) for e in n.elts]),
            ast.Tuple: lambda n: v.emitter.format_collection([v._v(e) for e in n.elts], "(", ")"),
            ast.Call: lambda n: ExpressionHandler.handle_call(v, n),
            ast.ListComp: lambda n: ExpressionHandler.handle_list_comp(v, n),
        }

    @staticmethod
    def handle_op(v, node):
        if isinstance(node, ast.BinOp):
            l, r = v._v(node.left), v._v(node.right)
            if isinstance(node.op, ast.Div): return v.emitter.format_binop(l, "/", r, is_div=True)
            op = constants.BIN_OPS.get(type(node.op))
            return v.emitter.format_binop(l, op, r) if op else v._unsupported(node.op)
        if isinstance(node, ast.UnaryOp):
            op = constants.UNARY_OPS.get(type(node.op))
            return v.emitter.format_unaryop(op, v._v(node.operand)) if op else v._unsupported(node.op)
        if isinstance(node, ast.BoolOp):
            op = constants.BOOL_OPS.get(type(node.op), "??")
            return v.emitter.format_boolop(op, [v._v(val) for val in node.values])
        if isinstance(node, ast.Compare):
            parts, curr = [], v._v(node.left)
            for op, comp in zip(node.ops, node.comparators):
                next_v = v._v(comp)
                parts.append(f"({curr} {constants.COMP_OPS.get(type(op), '?')} {next_v})")
                curr = next_v
            return v.emitter.format_compare(parts)

    @staticmethod
    def handle_call(v, node):
        from . import handlers  # 組み込みハンドラ参照用
        fn = v._v(node.func)
        # 組み込み関数やメソッドの特殊処理を確認
        h = BUILTIN_CALL_HANDLERS.get(fn) or (isinstance(node.func, ast.Attribute) and METHOD_CALL_HANDLERS.get(node.func.attr))
        if h:
            res = h(node, v)
            if res: return res
        args = [v._wrap(a, trigger_types=(ast.IfExp, ast.BinOp)) for a in node.args]
        return fn if not args else f"{fn} {' '.join(args)}"

    @staticmethod
    def handle_list_comp(v, node):
        current_lean_expr = v._v(node.elt)
        for i, gen in enumerate(reversed(node.generators)):
            target = v._v(gen.target)
            iterable = v._v(gen.iter)
            conditions = [v._v(c) for c in gen.ifs]
            cond_str = " && ".join(f"({c})" for c in conditions) if conditions else None
            current_lean_expr = v.emitter.format_list_comp_step(
                iterable, target, current_lean_expr, cond_str, is_innermost=(i == 0)
            )
        return current_lean_expr

class StatementHandler:
    """文（代入、関数定義、クラス定義など）のハンドラ"""
    @staticmethod
    def get_handlers(v):
        return {
            ast.Return: lambda n: v._v(n.value),
            ast.Expr: lambda n: v._v(n.value),
            ast.Assign: lambda n: v.emitter.format_assign(v._v(n.targets[0]), v._v(n.value)),
            ast.Assert: lambda n: v.emitter.format_assert(v._v(n.test)),
            ast.If: lambda n: v.emitter.format_if_stmt(v._v(n.test), [v._v(s) for s in n.body], [v._v(s) for s in n.orelse] if n.orelse else ["0"]),
            ast.FunctionDef: lambda n: StatementHandler.handle_function_def(v, n),
            ast.ClassDef: lambda n: StatementHandler.handle_class_def(v, n),
        }

    @staticmethod
    def handle_function_def(v, node):
        doc, stmts = v._extract_doc_and_body(node)
        args = v._format_args(node.args)
        is_thm = node.name.startswith(("verify_", "theorem_"))
        meta = v.context.functions.get(node.name, {})
        return v._build_function_or_theorem(node, doc, stmts, args, is_thm, meta)

    @staticmethod
    def handle_class_def(v, node):
        kind = v.context.classes.get(node.name)
        if kind == "enum":
            variants = [t.id for s in node.body if isinstance(s, ast.Assign) for t in s.targets if isinstance(t, ast.Name)]
            return v.emitter.format_inductive(node.name, variants)
        if kind == "structure":
            fields = [(s.target.id, types.translate_type(s.annotation)) for s in node.body if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name)]
            return v.emitter.format_structure(node.name, fields)
        return v._unsupported(node, "Only Enums and @dataclass are supported")

# 暫定的な組み込みハンドラ定義（必要に応じて core.py から移動）
BUILTIN_CALL_HANDLERS = {
    "sum": lambda n, v: f"py_sum {v._v(n.args[0])}",
    "len": lambda n, v: f"({v._v(n.args[0])}).length",
}
METHOD_CALL_HANDLERS = {
    "append": lambda n, v: f"{v._v(n.func.value)} ++ [{v._v(n.args[0])}]",
}