import ast
from .. import types
from . import constants
from . import handlers

class LeanTranslator(ast.NodeVisitor):
    """Python ASTを走査し、再帰的にLean 4の構文へと変換するメインビジター"""
    def __init__(self, context):
        self.context = context
        self.emitter = context.emitter
        # ディスパッチ・テーブル: 型をキーに関数をマッピング
        self.dispatch = {
            ast.Constant: lambda n: self.emitter.format_constant(n.value),
            ast.Name: lambda n: n.id,
            ast.Attribute: lambda n: self.emitter.format_attribute(self._v(n.value), n.attr),
            ast.Return: lambda n: self._v(n.value),
            ast.Expr: lambda n: self._v(n.value),
            ast.Assign: lambda n: self.emitter.format_assign(self._v(n.targets[0]), self._v(n.value)),
            ast.Pass: lambda _: "()",
            ast.Assert: lambda n: self.emitter.format_assert(self._v(n.test)),
            ast.IfExp: lambda n: self.emitter.format_if_exp(self._v(n.test), self._v(n.body), self._v(n.orelse)),
            ast.If: lambda n: self.emitter.format_if_stmt(self._v(n.test), [self._v(s) for s in n.body], [self._v(s) for s in n.orelse] if n.orelse else ["0"]),
            ast.List: lambda n: self.emitter.format_collection([self._v(e) for e in n.elts]),
            ast.Tuple: lambda n: self.emitter.format_collection([self._v(e) for e in n.elts], "(", ")"),
            # 演算子系は共通メソッドへ委譲
            ast.BinOp: self._visit_op,
            ast.UnaryOp: self._visit_op,
            ast.BoolOp: self._visit_op,
            ast.Compare: self._visit_op,
        }

    def visit_Module(self, node):
        """ルートノード: 全てのステートメントを変換して結合する"""
        return "\n\n".join(filter(None, [self.visit(stmt) for stmt in node.body]))

    def generic_visit(self, node):
        """未知のノードに対するデフォルトのフォールバック"""
        return self._unsupported(node)

    def visit(self, node):
        """ディスパッチ・テーブルを優先して参照する"""
        handler = self.dispatch.get(type(node))
        if handler: return handler(node)
        return super().visit(node)

    def _v(self, node):
        """再帰的な変換のヘルパー"""
        if node is None: return ""
        return self.visit(node)

    def _unsupported(self, node, detail=None):
        """サポート外の機能に遭遇した際の共通処理"""
        node_type = type(node).__name__
        msg = f"Python feature '{node_type}' is not supported yet"
        if detail: msg += f" ({detail})"
        self.context.add_warning(node, msg)
        return f"/- {msg} -/ sorry"

    def _extract_doc_and_body(self, node):
        """ノードからdocstringを除去した本体ステートメントを返す"""
        doc = ast.get_docstring(node)
        stmts = node.body
        # docstringが最初の式として存在する場合、bodyから除外
        if doc and stmts and isinstance(stmts[0], ast.Expr):
            stmts = stmts[1:]
        return doc, stmts

    def _format_args(self, args_node):
        """関数引数を (name : Type) の形式で結合する"""
        return " ".join([f"({a.arg} : {types.translate_type(a.annotation)})" for a in args_node.args])

    def _wrap(self, node, trigger_types=(ast.Call, ast.IfExp, ast.BinOp, ast.Compare)):
        """必要に応じて式を括弧で囲む"""
        res = self._v(node)
        if isinstance(node, trigger_types):
            return f"({res})"
        return res

    def visit_FunctionDef(self, node):
        doc, stmts = self._extract_doc_and_body(node)
        args = self._format_args(node.args)
        is_thm = node.name.startswith(("verify_", "theorem_"))
        meta = self.context.functions.get(node.name, {})
        return self._build_function_or_theorem(node, doc, stmts, args, is_thm, meta)

    def visit_ClassDef(self, node):
        """クラス定義をEnumまたはStructure(Dataclass)として変換する"""
        kind = self.context.classes.get(node.name)
        if kind == "enum":
            return self._translate_enum(node)
        if kind == "structure":
            return self._translate_structure(node)
        return self._unsupported(node, "Only Enums and @dataclass are supported")

    def _visit_op(self, node):
        """演算子系のノード（BinOp, UnaryOp, BoolOp, Compare）を統合処理する"""
        if isinstance(node, ast.BinOp):
            l, r = self._v(node.left), self._v(node.right)
            if isinstance(node.op, ast.Div): return self.emitter.format_binop(l, "/", r, is_div=True)
            op = constants.BIN_OPS.get(type(node.op))
            return self.emitter.format_binop(l, op, r) if op else self._unsupported(node.op)

        if isinstance(node, ast.UnaryOp):
            op = constants.UNARY_OPS.get(type(node.op))
            return self.emitter.format_unaryop(op, self._v(node.operand)) if op else self._unsupported(node.op)

        if isinstance(node, ast.BoolOp):
            op = constants.BOOL_OPS.get(type(node.op), "??")
            return self.emitter.format_boolop(op, [self._v(v) for v in node.values])

        if isinstance(node, ast.Compare):
            parts, curr = [], self._v(node.left)
            for op, comp in zip(node.ops, node.comparators):
                next_v = self._v(comp)
                parts.append(f"({curr} {constants.COMP_OPS.get(type(op), '?')} {next_v})")
                curr = next_v
            return self.emitter.format_compare(parts)

        return self._unsupported(node)

    def visit_Call(self, node):
        fn = self._v(node.func)
        h = handlers.BUILTIN_CALL_HANDLERS.get(fn) or (isinstance(node.func, ast.Attribute) and handlers.METHOD_CALL_HANDLERS.get(node.func.attr))
        if h:
            res = h(node, self)
            if res: return res
        args = [self._wrap(a, trigger_types=(ast.IfExp, ast.BinOp)) for a in node.args]
        return fn if not args else f"{fn} {' '.join(args)}"

    def visit_ListComp(self, node):
        return self._translate_list_comp(node.generators, node.elt)

    def visit_For(self, node): return "-- [PyLean] Error: for loops are not supported. Use list comprehensions or recursion."

    def _translate_enum(self, node):
        variants = [t.id
                    for s in node.body if isinstance(s, ast.Assign) 
                    for t in s.targets if isinstance(t, ast.Name)]
        return self.emitter.format_inductive(node.name, variants)

    def _translate_structure(self, node):
        fields = [(s.target.id, types.translate_type(s.annotation))
                  for s in node.body if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name)]
        return self.emitter.format_structure(node.name, fields)

    def _translate_list_comp(self, generators, elt):
        """
        リスト内包表記をLeanのmap/flatMap/filterMap/filterの組み合わせに変換する。
        再帰的なロジックを反復処理に置き換え、内側から外側へ式を構築する。
        """
        # 最終的にマップされる要素
        current_lean_expr = self._v(elt)

        # ジェネレータを逆順に処理することで、内側から外側へ式を構築する
        # Pythonのリスト内包表記の最後のジェネレータがLeanの最も内側の操作に対応する
        for i, gen in enumerate(reversed(generators)):
            target = self._v(gen.target)
            iterable = self._v(gen.iter)
            conditions = [self._v(c) for c in gen.ifs]
            cond_str = " && ".join(f"({c})" for c in conditions) if conditions else None
            
            # emitter を使って Lean の高階関数呼び出しを生成
            current_lean_expr = self.emitter.format_list_comp_step(
                iterable, target, current_lean_expr, cond_str, is_innermost=(i == 0)
            )

        return current_lean_expr

    def _build_function_or_theorem(self, node, doc, stmts, args, is_thm, meta):
        body_lines = [self._v(s) for s in stmts] or ["sorry"]

        if is_thm:
            # 定理の場合: 最後のReturnを命題として抽出し、本体からは除く
            is_ret = isinstance(stmts[-1], ast.Return)
            prop = self._v(stmts[-1].value) if is_ret else "True"
            if is_ret: body_lines = body_lines[:-1]
            return self.emitter.format_theorem(node.name, args, prop, body_lines, doc)
        else:
            return self.emitter.format_function(
                node.name, args, types.translate_type(node.returns), body_lines,
                doc=doc,
                termination_hint=meta.get("hint"),
                is_recursive=meta.get("is_recursive", False)
            )