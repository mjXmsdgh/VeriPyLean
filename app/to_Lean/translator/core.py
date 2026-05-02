import ast
from .. import types
from . import handlers

class LeanTranslator(ast.NodeVisitor):
    """
    Python ASTを再帰的に走査し、Lean 4のソースコードへと変換するメインロジッククラス。

    役割:
    - `ast.NodeVisitor`を継承し、各ASTノードを適切なハンドラ関数へ振り分ける。
    - 制御構造（If, Forなど）や関数定義の構造をLeanの構文へと再構成する。
    - 型変換や演算子のマッピングを統合し、最終的なLeanコードの断片を組み立てる。
    """
    def __init__(self, context):
        self.context = context
        # LeanEmitter は Lean の構文を文字列フォーマットするクラス
        from ..emitter import LeanEmitter
        self.emitter = LeanEmitter(context)
        
        # ASTノードタイプとハンドラの対応表
        self.dispatch = {
            ast.Constant: lambda n, v: f'"{n.value}"' if isinstance(n.value, str) else str(n.value),
            ast.Name: lambda n, v: n.id,
            ast.Attribute: lambda n, v: f"{v._v(n.value)}.{n.attr}",
            ast.Return: lambda n, v: v._v(n.value),
            ast.Expr: lambda n, v: v._v(n.value),
            ast.Assign: lambda n, v: f"let {v._v(n.targets[0])} := {v._v(n.value)};",
            ast.Assert: lambda n, v: f"have : {v._v(n.test)} := by sorry",
            ast.Pass: lambda n, v: "()",
            ast.IfExp: lambda n, v: f"if {v._v(n.test)} then {v._v(n.body)} else {v._v(n.orelse)}",
            ast.List: lambda n, v: f"[{', '.join([v._v(e) for e in n.elts])}]",
            ast.Tuple: lambda n, v: f"({', '.join([v._v(e) for e in n.elts])})",
            ast.BinOp: handlers.handle_op,
            ast.UnaryOp: handlers.handle_op,
            ast.BoolOp: handlers.handle_op,
            ast.Compare: handlers.handle_op,
            ast.If: handlers.handle_if,
            ast.FunctionDef: handlers.handle_function_def,
            ast.ClassDef: handlers.handle_class_def,
            ast.Call: handlers.handle_call,
            ast.ListComp: handlers.handle_list_comp,
        }

    def visit_Module(self, node):
        """ルートノード: 全てのステートメントを変換して結合する"""
        return "\n\n".join(filter(None, [self.visit(stmt) for stmt in node.body]))

    def visit(self, node):
        """ノードの種類に応じてハンドラを呼び出す"""
        handler = self.dispatch.get(type(node))
        if handler:
            return handler(node, self)
        return super().visit(node)

    def _v(self, node):
        """再帰的な visit のエイリアス"""
        return self.visit(node)

    def _wrap(self, node, trigger_types=(ast.IfExp, ast.BinOp)):
        """必要に応じて括弧で囲む補助関数"""
        res = self._v(node)
        return f"({res})" if isinstance(node, trigger_types) else res

    def _unsupported(self, node, msg=""):
        return f"-- [Unsupported] {type(node).__name__}: {msg}"

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

    def _build_function_or_theorem(self, node, doc, stmts, args, is_thm, meta):
        """関数(def)または定理(theorem)の構造を組み立てる"""
        body_lines = [self._v(s) for s in stmts] or ["sorry"]

        if is_thm:
            # 定理の場合: 最後のReturnを命題として抽出し、本体からは除く
            is_ret = isinstance(stmts[-1], ast.Return)
            prop = self._v(stmts[-1].value) if is_ret else "True"
            if is_ret: body_lines = body_lines[:-1]
            return self.emitter.format_theorem(node.name, args, prop, body_lines, doc)
        else:
            return self.emitter.format_function(
                node.name, args, types.translate_type(node.returns, self.context), body_lines,
                doc=doc,
                termination_hint=meta.get("hint"),
                is_recursive=meta.get("is_recursive", False)
            )

def translate_to_lean(node, context=None):
    """ASTノードをLeanコード文字列に変換する"""
    if context is None:
        from .context import TranslationContext
        context = TranslationContext()
    visitor = LeanTranslator(context)
    return visitor.visit(node)