import ast

def analyze(node, context=None):
    """ASTの静的解析を行い、コンテキスト情報を構築する (Perform static analysis on AST and build context)"""
    if context is None:
        from .context import TranslationContext
        context = TranslationContext()
    
    analyzer = SafetyAnalyzer(context)
    analyzer.analyze(node)
    return context

class SafetyAnalyzer(ast.NodeVisitor):
    """
    Python ASTを走査し、形式検証（Leanへの変換）の前にコードの安全性を静的に解析するクラス。

    役割:
    - ゼロ除算などの実行時エラーの可能性がある箇所を特定する。
    - ガード条件（if文など）がない危険な操作に対し、`TranslationContext`を通じて警告を発行する。
    - 将来的に、事前条件や不変条件の不備を指摘するためのフックとして機能する。
    """
    def __init__(self, context):
        self.context = context
        self.current_guards = []

    def analyze(self, node):
        """Starts the safety analysis on the provided AST node."""
        self.visit(node)

    def visit_BinOp(self, node):
        """Heuristic to detect division operations and verify safety guards."""
        if isinstance(node.op, (ast.Div, ast.FloorDiv)):
            # Basic heuristic: check if the operation is guarded by a conditional check.
            # In v0.1, this can be expanded to interface with the TranslationContext 
            # to raise warnings if no safety guards (e.g., 'if b != 0') are found.
            if isinstance(node.right, ast.Constant) and node.right.value == 0:
                self.context.add_warning(node, "Potential division by zero detected.")
            elif isinstance(node.right, ast.Name):
                # 将来的にはガード条件の有無をここでチェックする
                self.context.add_warning(node, f"Division by variable '{node.right.id}' requires safety proof.")
        self.generic_visit(node)