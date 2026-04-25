import ast

def get_parent_if(node, tree):
    """
    指定されたノードを包んでいる ast.If ノードを探して返す（ガード条件の特定に使用）
    """
    # 簡易的な実装: 実際には NodeVisitor や parent 指向の解析が必要
    return None

def is_guarded_by_zero_check(node, var_name):
    """
    変数 var_name が 0 でないことを確認する if 文の中で node が実行されているか判定する
    """
    # 今後の実装予定:
    # 1. node の親を遡り ast.If を見つける
    # 2. その test 属性が 'var_name != 0' や 'var_name > 0' であるかを確認する
    return False

def get_full_name(node):
    """ast.Name や ast.Attribute から完全な変数名を取得する"""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{get_full_name(node.value)}.{node.attr}"
    return None