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

    def visit_If(self, node):
        """分岐の網羅性と到達可能性を解析する"""
        # 1. 網羅性チェック: else ブロックの欠如を確認
        if not node.orelse:
            self.context.add_warning(node, "Exhaustiveness: Missing 'else' block. In Lean, functions must be exhaustive.")
        
        # 2. 到達可能性チェック: if-elif チェーンを辿って論理的矛盾を検知
        self._analyze_if_chain_reachability(node)
        
        self.generic_visit(node)

    def _analyze_if_chain_reachability(self, node):
        """
        if-elif チェーンを解析し、条件の重複や順序の誤りによる到達不能コードを検知する。
        例: if income <= 5000: ... elif income <= 2000: ... (2000のケースは絶対に来ない)
        """
        constraints = []
        curr = node
        while isinstance(curr, ast.If):
            comp = self._try_extract_comparison(curr.test)
            if comp:
                var_name, op, val = comp
                # 過去の条件と比較して論理的な矛盾をチェック
                for prev_var, prev_op, prev_val in constraints:
                    if prev_var == var_name:
                        self._check_shadowing(curr, var_name, prev_op, prev_val, op, val)
                constraints.append(comp)

            # 次の elif (orelse 内の唯一の If) へ移動
            curr = curr.orelse[0] if (len(curr.orelse) == 1 and isinstance(curr.orelse[0], ast.If)) else None

    def _try_extract_comparison(self, test):
        """単純な '変数 op 定数' の比較式 (var op constant) を抽出する"""
        if (isinstance(test, ast.Compare) and len(test.ops) == 1 and
            isinstance(test.left, ast.Name) and isinstance(test.comparators[0], ast.Constant) and
            isinstance(test.comparators[0].value, (int, float))):
            return test.left.id, test.ops[0], test.comparators[0].value
        return None

    def _check_shadowing(self, node, var, prev_op, prev_val, curr_op, curr_val):
        """特定の演算パターンにおける shadowing (条件の包含) を検知する"""
        # パターン: if x <= 5000: ... elif x <= 2000: ...
        if isinstance(prev_op, ast.LtE) and isinstance(curr_op, (ast.LtE, ast.Lt)):
            if prev_val >= curr_val:
                self.context.add_warning(node, f"Logic Inconsistency: condition '{var} {type(curr_op).__name__} {curr_val}' is unreachable because it is shadowed by a previous '{var} <= {prev_val}'")
        
        # パターン: if x >= 2000: ... elif x >= 5000: ...
        elif isinstance(prev_op, ast.GtE) and isinstance(curr_op, (ast.GtE, ast.Gt)):
            if prev_val <= curr_val:
                self.context.add_warning(node, f"Logic Inconsistency: condition '{var} {type(curr_op).__name__} {curr_val}' is unreachable because it is shadowed by a previous '{var} >= {prev_val}'")

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