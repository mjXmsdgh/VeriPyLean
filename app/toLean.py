import ast

# --- 変換ロジック (ルールベースの核) ---
def translate_to_lean(node):
    if node is None:
        return ""

    # 数値
    if isinstance(node, ast.Constant):
        return str(node.value)
    
    # 変数
    elif isinstance(node, ast.Name):
        return node.id
    
    # Return文（中身をさらに解析）
    elif isinstance(node, ast.Return):
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