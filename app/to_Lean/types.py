import ast

# Lean 4 標準型へのマッピング
TYPE_MAP = {
    "int": "Int",
    "float": "Float",
    "str": "String",
    "bool": "Bool",
    "Decimal": "Rat",
    "date": "Date",
    "None": "Unit",
    "list": "List Int",
    "dict": "AssocList Int Int",
}

# ジェネリクス名の変換ルール
GENERIC_MAP = {
    "List": "List",
    "Optional": "Option",
    "Dict": "AssocList",
}

def translate_type(node, context=None):
    """
    PythonのASTノード（型ヒント）をLean 4の型文字列に変換する。
    ジェネリクスやコンテキスト内のユーザー定義クラスの解決をサポート。
    """
    if node is None:
        return "Int"  # 型ヒントがない場合のデフォルト

    # 1. 単純な名前 (int, str, UserClass 等)
    if isinstance(node, ast.Name):
        name = node.id
        if name in TYPE_MAP:
            return TYPE_MAP[name]
        # AnalysisVisitorで収集されたクラス情報を確認
        if context and name in context.classes:
            return name
        return name

    # 2. ジェネリクス (List[int], Optional[float] 等)
    if isinstance(node, ast.Subscript):
        # 基底型 (List等) を取得
        base_name = getattr(node.value, "id", "")
        lean_base = GENERIC_MAP.get(base_name, translate_type(node.value, context))
        
        # 内包される型 (T) を再帰的に解決
        # Python 3.9+ の AST 構造に対応 (node.slice が直接ノード)
        inner_node = node.slice
        if isinstance(inner_node, ast.Tuple):
            # Dict[K, V] のように複数のパラメータがある場合
            inner_types = [translate_type(elt, context) for elt in inner_node.elts]
            return f"{lean_base} {' '.join(inner_types)}"
        return f"{lean_base} {translate_type(inner_node, context)}"

    # 3. 属性アクセス (datetime.date 等)
    if isinstance(node, ast.Attribute):
        return TYPE_MAP.get(node.attr, node.attr)

    return "Int"