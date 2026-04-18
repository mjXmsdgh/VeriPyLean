import ast
from . import handlers

class LeanTranslator(ast.NodeVisitor):
    """Python AST を走査し、Lean 4 コードを生成するメインクラス"""
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

def translate_to_lean(node, context=None):
    """ASTノードをLeanコード文字列に変換する"""
    if context is None:
        from .context import TranslationContext
        context = TranslationContext()
    visitor = LeanTranslator(context)
    return visitor.visit(node)