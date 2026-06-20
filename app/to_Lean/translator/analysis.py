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
        self.current_function = None
        self.current_function_args = set()
        self.defined_vars = set()

    def analyze(self, node):
        """Starts the safety analysis on the provided AST node."""
        self.visit(node)

    def visit_FunctionDef(self, node):
        """関数のスコープを開始し、引数を定義済みリストに入れる"""
        prev_func = self.current_function
        prev_vars = self.defined_vars.copy()
        prev_args = self.current_function_args.copy()
        
        self.current_function = node.name
        self.current_function_args = {arg.arg for arg in node.args.args}
        
        # 引数を定義済みに追加
        for arg in node.args.args:
            self.defined_vars.add(arg.arg)
            
        if node.name not in self.context.functions:
            self.context.functions[node.name] = {}
        self.context.functions[node.name]["loop_info"] = []
        self.context.functions[node.name]["preconditions"] = []

        self.generic_visit(node)
        
        self.defined_vars = prev_vars
        self.current_function = prev_func
        self.current_function_args = prev_args

    def visit_Assert(self, node):
        """assert文を解析し、事前条件としての適性を判定する"""
        if self.current_function:
            # assertの条件式で使用されている変数を抽出
            used_vars = {n.id for n in ast.walk(node.test) if isinstance(n, ast.Name)}
            # 使用されている変数がすべて関数の引数である場合、事前条件として登録
            if used_vars.issubset(self.current_function_args) and len(used_vars) > 0:
                if "preconditions" not in self.context.functions[self.current_function]:
                    self.context.functions[self.current_function]["preconditions"] = []
                self.context.functions[self.current_function]["preconditions"].append(node.test)
        self.generic_visit(node)

    def visit_Assign(self, node):
        """代入された変数を現在のスコープの定義済みリストに記録する"""
        for t in node.targets:
            if isinstance(t, ast.Name):
                self.defined_vars.add(t.id)
        self.generic_visit(node)

    def visit_For(self, node):
        """ループ内で更新され、かつループ外で定義済みの変数を『状態変数』として抽出する"""
        # 1. ループ内で代入が行われている変数を特定
        updated_in_loop = self._find_updated_variables(node.body)
        
        # 2. ループ開始時点で定義済みの変数との積集合をとる
        state_vars = updated_in_loop.intersection(self.defined_vars)
        
        if self.current_function:
            self.context.functions[self.current_function]["loop_info"].append({
                "state_vars": list(state_vars),
                "node": node
            })
        
        # 3. ループのインデックス変数も定義済みに追加
        if isinstance(node.target, ast.Name):
            self.defined_vars.add(node.target.id)
            
        self.generic_visit(node)

    def _find_updated_variables(self, body):
        """ループのボディを走査し、代入対象となっている変数名のセットを返す"""
        updated = set()
        for stmt in body:
            for sub_node in ast.walk(stmt):
                if isinstance(sub_node, ast.Assign):
                    for target in sub_node.targets:
                        if isinstance(target, ast.Name):
                            updated.add(target.id)
                elif isinstance(sub_node, ast.AugAssign):
                    if isinstance(sub_node.target, ast.Name):
                        updated.add(sub_node.target.id)
        return updated

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
            if isinstance(node.right, ast.Constant) and node.right.value == 0:
                self.context.add_warning(node, "Potential division by zero detected.")
            elif isinstance(node.right, ast.Name):
                # ガード条件の有無（preconditions）を確認する
                guarded = False
                if self.current_function:
                    meta = self.context.functions.get(self.current_function, {})
                    preconds = meta.get("preconditions", [])
                    # 定理の場合、被検証関数のpreconditionsも確認する
                    if self.current_function.startswith(("verify_", "theorem_")):
                        target_name = self.current_function.replace("verify_", "").replace("theorem_", "")
                        target_meta = self.context.functions.get(target_name, {})
                        preconds = target_meta.get("preconditions", [])
                    
                    for cond in preconds:
                        if isinstance(cond, ast.Compare) and len(cond.ops) == 1:
                            left = cond.left
                            op = cond.ops[0]
                            right = cond.comparators[0]
                            if isinstance(left, ast.Name) and left.id == node.right.id:
                                # divisor > 0 or divisor != 0 or divisor < 0 などをチェック
                                if isinstance(op, (ast.Gt, ast.GtE, ast.Lt, ast.LtE, ast.NotEq)):
                                    if isinstance(right, ast.Constant) and right.value == 0:
                                        guarded = True
                                        break
                if not guarded:
                    self.context.add_warning(node, f"Division by variable '{node.right.id}' requires safety proof.")
        self.generic_visit(node)