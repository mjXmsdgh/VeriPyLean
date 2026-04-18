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
            ast.If: lambda n: handlers.handle_if(n, self),
            ast.List: lambda n: f"[{', '.join([self._v(e) for e in n.elts])}]",
            ast.Tuple: lambda n: f"({', '.join([self._v(e) for e in n.elts])})",
            ast.ListComp: lambda n: handlers.handle_list_comp(n, self),
            ast.For: lambda n: self._unsupported(n, "Use list comprehensions or recursion instead of for-loops"),
            ast.BinOp: lambda n: handlers.handle_op(n, self),
            ast.UnaryOp: lambda n: handlers.handle_op(n, self),
            ast.BoolOp: lambda n: handlers.handle_op(n, self),
            ast.Compare: lambda n: handlers.handle_op(n, self),
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
        return handlers.handle_function_def(node, self)

    def visit_ClassDef(self, node):
        return handlers.handle_class_def(node, self)

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

    def visit_Call(self, node):
        return handlers.handle_call(node, self)