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
            "Decimal": "Rat",    # Decimalは有理数(Rat)へ
            "date": "Date"       # datetime.dateはDate構造体へ
        }
        return mapping.get(node.id, "Int")
    
    # 複雑な型や未対応の型はデフォルトで Int を返す
    return "Int"