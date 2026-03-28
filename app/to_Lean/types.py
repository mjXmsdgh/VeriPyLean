import ast

def translate_type(node):
    """
    Pythonの型注釈(ASTノード)をLeanの型名文字列に変換する
    """
    # 型ヒントがない場合はデフォルトでIntとする（サンプル解説に基づく）
    if node is None:
        return "Int"
    
    if isinstance(node, ast.Name):
        # 基本型のマッピング
        mapping = {
            "int": "Int",
            "float": "Float",
            "str": "String",
            "bool": "Bool",
            "list": "List Int",  # リストの中身は一旦 Int と仮定
            "List": "List",      # Subscript 処理用
            "Optional": "Option",# Subscript 処理用
            "Decimal": "Rat",    # Decimalは有理数(Rat)へ
            "date": "Date"       # datetime.dateはDate構造体へ
        }
        # マッピングにない場合は、カスタム型（EnumやStructure）とみなしてそのまま返す
        return mapping.get(node.id, node.id)

    if isinstance(node, ast.Subscript):
        # List[T] や Optional[T] のような形式を処理
        container_type = translate_type(node.value)
        
        # Python 3.9+ の slice 構造に対応 (Indexノードの有無を考慮)
        inner_node = node.slice
        if hasattr(ast, 'Index') and isinstance(inner_node, ast.Index):
            inner_node = inner_node.value
            
        inner_type = translate_type(inner_node)
        return f"{container_type} {inner_type}"
    
    return "Int"