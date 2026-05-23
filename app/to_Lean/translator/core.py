import ast
from .. import types, handlers
from . import constants

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
        self.current_function = None
        # LeanEmitter は Lean の構文を文字列フォーマットするクラス
        from ..emitter import LeanEmitter
        self.emitter = LeanEmitter(context)
        
        # ASTノードタイプとハンドラの対応表
        self.dispatch = {
            ast.Constant: lambda n, v: (
                v.emitter.format_rat_constant(n.value) 
                if isinstance(n.value, float) 
                else v.emitter.format_constant(n.value)
            ),
            ast.Name: lambda n, v: n.id,
            ast.Attribute: lambda n, v: v.emitter.format_attribute(v._v(n.value), n.attr),
            ast.Return: lambda n, v: v._v(n.value),
            ast.Expr: lambda n, v: v._v(n.value),
            ast.Assign: lambda n, v: v.emitter.format_assign(v._v(n.targets[0]), v._v(n.value)),
            ast.AugAssign: lambda n, v: handlers.StatementHandler.handle_aug_assign(v, n),
            ast.Assert: lambda n, v: v.emitter.format_assert(v._v(n.test)),
            ast.Pass: lambda n, v: "()",
            ast.IfExp: lambda n, v: v.emitter.format_if_exp(v._v(n.test), v._v(n.body), v._v(n.orelse)),
            ast.List: lambda n, v: v.emitter.format_collection([v._v(e) for e in n.elts]),
            ast.Tuple: lambda n, v: v.emitter.format_collection([v._v(e) for e in n.elts], "(", ")"),
            ast.BinOp: lambda n, v: handlers.ExpressionHandler.handle_op(v, n),
            ast.UnaryOp: lambda n, v: handlers.ExpressionHandler.handle_op(v, n),
            ast.BoolOp: lambda n, v: handlers.ExpressionHandler.handle_op(v, n),
            ast.Compare: lambda n, v: handlers.ExpressionHandler.handle_op(v, n),
            ast.If: lambda n, v: handlers.StatementHandler.handle_if(v, n),
            ast.FunctionDef: self.visit_FunctionDef,
            ast.For: self.visit_For,
            ast.ClassDef: lambda n, v: handlers.StatementHandler.handle_class_def(v, n),
            ast.Call: lambda n, v: handlers.ExpressionHandler.handle_call(v, n),
            ast.ListComp: lambda n, v: handlers.ExpressionHandler.handle_list_comp(v, n),
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

    def visit_FunctionDef(self, node, v):
        """関数定義の変換。解析情報の参照用に現在の関数名を記録する。"""
        old_func = self.current_function
        self.current_function = node.name
        res = handlers.StatementHandler.handle_function_def(v, node)
        self.current_function = old_func
        return res

    def visit_For(self, node, v):
        """
        forループをLeanの末尾再帰構造（let rec）に変換する。
        1. 解析フェーズで特定した状態変数を引数に取る。
        2. ループ回数を Nat のデクリメントとして表現する。
        """
        if not self.current_function:
            return self._unsupported(node, "Loop outside of function scope")

        # 1. 解析フェーズで取得した状態変数の情報を引き出す
        loop_info = None
        func_meta = self.context.functions.get(self.current_function, {})
        for info in func_meta.get("loop_info", []):
            if info["node"] == node:
                loop_info = info
                break

        if not loop_info or not (isinstance(node.iter, ast.Call) and getattr(node.iter.func, 'id', '') == 'range'):
            return self._unsupported(node, "Only simple 'for i in range(n)' loops are supported for recursion conversion")

        state_vars = loop_info["state_vars"]  # ['balance'] など
        limit_expr = self._v(node.iter.args[0])
        
        # 2. 引数リスト、戻り値の型、およびベースケースの戻り値を構築
        typed_args = " ".join([f"({var} : Rat)" for var in state_vars])
        current_state_args = " ".join(state_vars)
        
        if len(state_vars) == 1:
            base_return = state_vars[0]
            ret_type = "Rat"
        else:
            base_return = f"({', '.join(state_vars)})"
            ret_type = "(" + " × ".join(["Rat"] * len(state_vars)) + ")"
        
        # 3. ループボディの計算式を再帰呼び出しの引数へと変換
        # Pythonの副作用（代入）は、Leanでは let 式の連続として表現される
        body_lines = [self._v(stmt) for stmt in node.body]
        
        # 4. Lean 4 の let rec 構文を組み立てる
        # ステップ 4: ベースケース（終了条件）の設定
        res = [
            f"let rec loop (n : Nat) {typed_args} : {ret_type} :=",
            f"  if n = 0 then {base_return}",
            f"  else",
            f"    {chr(10).join(['    ' + line for line in body_lines])}",
            f"    loop (n - 1) {current_state_args}",
            f"  termination_by n"
        ]
        
        # 初期呼び出しと状態のバインド
        # ステップ 5: 停止性の保証と型の整合性 (Int -> Nat)
        res_call = f"loop ({limit_expr}).toNat {current_state_args}"
        if len(state_vars) == 1:
            binding = f"let {state_vars[0]} := {res_call};"
        else:
            binding = f"let ({', '.join(state_vars)}) := {res_call};"

        return "\n".join(res) + "\n" + binding

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