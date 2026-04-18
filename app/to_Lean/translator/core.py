import ast
from .. import types
from . import constants
from . import handlers
from .emitter import LeanEmitter

class LeanTranslator(ast.NodeVisitor):
    """Python ASTを走査し、再帰的にLean 4の構文へと変換するメインビジター"""
    def __init__(self, context):
        self.context = context
        self.emitter = LeanEmitter(context)
        # ディスパッチ・テーブル: 変換ロジックをマッピング
        self.dispatch = {
            ast.Constant: lambda n: f'"{n.value}"' if isinstance(n.value, str) else str(n.value),
            ast.Name: lambda n: n.id,
            ast.Attribute: lambda n: f"{self._v(n.value)}.{n.attr}",
            ast.Return: lambda n: self._v(n.value),
            ast.Expr: lambda n: self._v(n.value),
            ast.Assign: lambda n: self.emitter.format_let(self._v(n.targets[0]), self._v(n.value)),
            ast.Assert: lambda n: self.emitter.format_have(self._v(n.test)),
            ast.Pass: lambda _: "()",
            ast.IfExp: lambda n: self.emitter.format_if_expr(self._v(n.test), self._v(n.body), self._v(n.orelse)),
            ast.List: lambda n: f"[{', '.join([self._v(e) for e in n.elts])}]",
            ast.Tuple: lambda n: f"({', '.join([self._v(e) for e in n.elts])})",
            ast.ListComp: lambda n: self._translate_list_comp(n.generators, n.elt),
            ast.For: lambda n: self._unsupported(n, "Use list comprehensions or recursion instead of for-loops"),
            # 演算子系は共通メソッドへ委譲
            ast.BinOp: self._visit_op,
            ast.UnaryOp: self._visit_op,
            ast.BoolOp: self._visit_op,
            ast.Compare: self._visit_op,
        }

    def visit_Module(self, node):
        """ルートノード: 全てのステートメントを変換して結合する"""
        return "\n\n".join(filter(None, [self.visit(stmt) for stmt in node.body]))

    def visit(self, node):
        """ディスパッチ・テーブルを優先して参照する"""
        handler = self.dispatch.get(type(node))
        if handler: return handler(node)
        return super().visit(node)

    def generic_visit(self, node):
        """未知のノードに対するデフォルトのフォールバック"""
        return self._unsupported(node)

    def _v(self, node):
        """再帰的な変換のヘルパー"""
        if node is None: return ""
        return self.visit(node)

    def _unsupported(self, node, detail=None):
        """サポート外の機能に遭遇した際の共通処理"""
        node_type = type(node).__name__
        line = getattr(node, 'lineno', '?')
        col = getattr(node, 'col_offset', '?')
        msg = f"Python feature '{node_type}' is not supported yet"
        if detail: msg += f" ({detail})"
        self.context.add_warning(node, msg)
        return f"/- [Line {line}, Col {col}] {msg} -/ sorry"

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
        return " ".join([f"({a.arg} : {types.translate_type(a.annotation, self.context)})" for a in args_node.args])

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
        # 演算子のカテゴリごとにフォーマット処理を振り分ける
        if isinstance(node, ast.BinOp):
            return self._format_binop(node)
        if isinstance(node, ast.UnaryOp):
            op = constants.UNARY_OPS.get(type(node.op))
            return f"({op}{self._wrap(node.operand)})" if op else self._unsupported(node)
        if isinstance(node, ast.BoolOp):
            op = constants.BOOL_OPS.get(type(node.op), "??")
            return f"({(f' {op} ').join([self._wrap(v) for v in node.values])})"
        if isinstance(node, ast.Compare):
            return self._format_compare(node)
        return self._unsupported(node)

    def _format_binop(self, node):
        """二項演算をフォーマットする。/ (Div) は特殊なヘルパーに変換する。"""
        l, r = self._wrap(node.left), self._wrap(node.right)
        if isinstance(node.op, ast.Div):
            return f"(py_div {l} {r})"
        op = constants.BIN_OPS.get(type(node.op))
        return f"({l} {op} {r})" if op else self._unsupported(node)

    def _format_compare(self, node):
        """連結比較 (a < b < c) を Lean の論理積に展開する"""
        parts = []
        curr_left = node.left
        for op_node, next_node in zip(node.ops, node.comparators):
            op = constants.COMP_OPS.get(type(op_node), "?")
            parts.append(f"({self._v(curr_left)} {op} {self._v(next_node)})")
            curr_left = next_node
        return parts[0] if len(parts) == 1 else f"({' && '.join(parts)})"

    def _get_block_lines(self, stmts, is_theorem=False):
        """複数のステートメントを変換し、行のリストとして返す"""
        if not stmts:
            return ["()" if not is_theorem else "True"]
        
        lines = []
        for i, stmt in enumerate(stmts):
            lines.append(self._v(stmt))
            if i == len(stmts) - 1:
                if isinstance(stmt, (ast.Assign, ast.Assert)):
                    lines.append("()" if not is_theorem else "True")
        return lines

    def visit_If(self, node):
        then_lines = self._get_block_lines(node.body)
        else_lines = self._get_block_lines(node.orelse) if node.orelse else None
        return self.emitter.format_if_stmt(self._v(node.test), then_lines, else_lines)

    def visit_Call(self, node):
        fn = self._v(node.func)
        h = handlers.BUILTIN_CALL_HANDLERS.get(fn) or (isinstance(node.func, ast.Attribute) and handlers.METHOD_CALL_HANDLERS.get(node.func.attr))
        if h:
            res = h(node, self)
            if res: return res
        args = [self._wrap(a, trigger_types=(ast.IfExp, ast.BinOp)) for a in node.args]
        return fn if not args else f"{fn} {' '.join(args)}"

    def _translate_enum(self, node):
        variants = []
        for s in node.body:
            if isinstance(s, ast.Assign):
                for t in s.targets:
                    if isinstance(t, ast.Name):
                        variants.append(t.id)
        return self.emitter.format_inductive(node.name, variants)

    def _translate_structure(self, node):
        fields = []
        for s in node.body:
            if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name):
                fields.append((
                    s.target.id, 
                    types.translate_type(s.annotation, self.context)
                ))
        return self.emitter.format_structure(node.name, fields)

    def _translate_list_comp(self, generators, elt):
        """リスト内包表記を map/flatMap/filter/filterMap の組み合わせに反復的に変換する"""
        current_expr = self._v(elt)

        # 内側（最後）のジェネレータから外側に向かって式を構築する
        for i, gen in enumerate(reversed(generators)):
            target = self._v(gen.target)
            iterable = self._v(gen.iter)
            cond = " && ".join(f"({self._v(c)})" for c in gen.ifs) if gen.ifs else None
            
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

    def _build_function_or_theorem(self, node, doc, stmts, args, is_thm, meta):
        is_ret = is_thm and isinstance(stmts[-1], ast.Return)
        body_stmts = stmts[:-1] if is_ret else stmts
        
        if is_thm:
            prop = self._v(stmts[-1].value) if is_ret else "True"
            body_lines = self._get_block_lines(body_stmts, is_theorem=True)
            return self.emitter.format_theorem(node.name, args, prop, body_lines, doc=doc)
        else:
            ret_type = types.translate_type(node.returns, self.context)
            body_lines = self._get_block_lines(body_stmts, is_theorem=False)
            return self.emitter.format_function(
                node.name, args, ret_type, body_lines, 
                doc=doc, 
                termination_hint=meta.get("hint"),
                is_recursive=meta.get("is_recursive")
            )