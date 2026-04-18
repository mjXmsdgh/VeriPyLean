import ast
from typing import Tuple, Optional
from .context import TranslationContext

class AnalysisVisitor(ast.NodeVisitor):
    """
    Leanコード生成パスの前に実行され、ASTから意味情報を抽出する。
    
    役割:
    1. 関数が自己再帰しているか判定し、停止性のためのヒント（引数の減少）を探す。
    2. クラス定義がEnumなのかDataclassなのかを判定し、生成パスでの分岐を簡略化する。
    """
    def __init__(self, context):
        self.context = context

    def visit_ClassDef(self, node):
        is_enum = any(isinstance(b, ast.Name) and b.id == "Enum" for b in node.bases)
        is_dc = any((isinstance(d, ast.Name) and d.id == "dataclass") or 
                    (isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "dataclass") 
                    for d in node.decorator_list)
        if is_enum: self.context.classes[node.name] = "enum"
        elif is_dc: self.context.classes[node.name] = "structure"
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        """関数定義を見つけたら再帰構造を解析してコンテキストに登録する"""
        is_rec, hint = self._check_recursion(node)
        self.context.functions[node.name] = {"is_recursive": is_rec, "hint": hint}
        self.generic_visit(node)

    def _check_recursion(self, func_node) -> Tuple[bool, Optional[str]]:
        """
        関数内のCallノードを調べ、自己再帰の有無と停止性ヒント(n-1 等)を抽出する。

        Args:
            func_node (ast.FunctionDef): 解析対象の関数定義。

        Returns:
            Tuple[bool, Optional[str]]: (再帰の有無, 減少する引数名)
        """
        func_name = func_node.name
        res = {"is_recursive": False, "hint": None}
        
        class RecursionChecker(ast.NodeVisitor):
            def visit_Call(self, call_node):
                if isinstance(call_node.func, ast.Name) and call_node.func.id == func_name:
                    res["is_recursive"] = True
                    # 停止性ヒントの簡易抽出 (n - 1 などのパターン)
                    for i, arg in enumerate(call_node.args):
                        if (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub) and 
                            isinstance(arg.left, ast.Name) and i < len(func_node.args.args) and
                            arg.left.id == func_node.args.args[i].arg):
                            res["hint"] = arg.left.id
                self.generic_visit(call_node)
        
        RecursionChecker().visit(func_node)
        return res["is_recursive"], res["hint"]

def analyze(node, context=None):
    """ASTを解析してコンテキストに情報を格納する"""
    if context is None:
        context = TranslationContext()
    visitor = AnalysisVisitor(context)
    visitor.visit(node)
    return context