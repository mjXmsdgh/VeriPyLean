import ast
from .. import types
from . import constants
from . import handlers

class LeanTranslator(ast.NodeVisitor):
    """Python ASTを走査し、再帰的にLean 4の構文へと変換するメインビジター"""
    def __init__(self, context):
        self.context = context
        self.emitter = context.emitter
        self.dispatch = self._build_dispatch_table()

    def _build_dispatch_table(self):
        """各ハンドラクラスからマッピングをマージする"""
        table = {}
        table.update(handlers.BaseHandler.get_handlers(self))
        table.update(handlers.ExpressionHandler.get_handlers(self))
        table.update(handlers.StatementHandler.get_handlers(self))
        return table

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

    def visit_For(self, node): return "-- [PyLean] Error: for loops are not supported. Use list comprehensions or recursion."

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