import ast

# --- 型変換のヘルパー関数 ---
def translate_type(annotation_node):
    """Pythonの型ヒントASTノードをLeanの型文字列に変換する"""
    if annotation_node is None:
        return "Int"  # 型ヒントがない場合のデフォルト
    if isinstance(annotation_node, ast.Name):
        type_map = {
            'int': 'Int',
            'str': 'String',
            'bool': 'Bool',
            'float': 'Float', # Lean 4にはFloat型がある
        }
        return type_map.get(annotation_node.id, "Int") # マップにない場合はIntにフォールバック
    return "Int" # サポート外の型ヒント形式

# --- 変換ロジック (ルールベースの核) ---
def translate_to_lean(node):
    if node is None:
        return ""

    # 関数定義
    if isinstance(node, ast.FunctionDef):
        func_name = node.name
        # 引数の型を解決
        args_list = []
        for arg in node.args.args:
            arg_name = arg.arg
            arg_type = translate_type(arg.annotation)
            args_list.append(f"({arg_name} : {arg_type})")
        args = " ".join(args_list)
        # 戻り値の型を解決
        return_type = translate_type(node.returns)
        # body[0] は return 文などを想定
        body = translate_to_lean(node.body[0])
        return f"def {func_name} {args} : {return_type} :=\n  {body}"

    # 定数（数値、文字列など）
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return f'"{node.value}"'  # 文字列はダブルクォートで囲む
        return str(node.value)
    
    # 変数
    elif isinstance(node, ast.Name):
        return node.id
    
    # Return文（中身をさらに解析）
    elif isinstance(node, ast.Return):
        return translate_to_lean(node.value)

    # 式 (ast.Expr)
    elif isinstance(node, ast.Expr):
        return translate_to_lean(node.value)

    # 二項演算 (// や + など)
    elif isinstance(node, ast.BinOp):
        left = translate_to_lean(node.left)
        right = translate_to_lean(node.right)
        if isinstance(node.op, (ast.Div, ast.FloorDiv)):
            return f"({left} / {right})"
        elif isinstance(node.op, ast.Add):
            return f"({left} + {right})"
        elif isinstance(node.op, ast.Sub):
            return f"({left} - {right})"
        elif isinstance(node.op, ast.Mult):
            return f"({left} * {right})"
        elif isinstance(node.op, ast.Mod):
            return f"({left} % {right})"

    # 条件式 (if ... else ...)
    elif isinstance(node, ast.IfExp):
        test = translate_to_lean(node.test)
        body = translate_to_lean(node.body)
        orelse = translate_to_lean(node.orelse)
        return f"if {test} then {body} else {orelse}"

    # 条件分岐
    elif isinstance(node, ast.If):
        test = translate_to_lean(node.test)
        # 0番目の要素を再帰的に変換
        body = translate_to_lean(node.body[0]) 
        orelse = translate_to_lean(node.orelse[0]) if node.orelse else "0"
        return f"if {test} then {body} else {orelse}"

    # 比較 (b != 0)
    elif isinstance(node, ast.Compare):
        left = translate_to_lean(node.left)
        op = "≠" if isinstance(node.ops[0], ast.NotEq) else "=="
        right = translate_to_lean(node.comparators[0])
        return f"{left} {op} {right}"
    
    return "/* サポート外 */"