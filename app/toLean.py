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

# --- 各ASTノードに対応する変換関数 ---

def _translate_function_def(node):
    """ast.FunctionDef をLeanの関数定義に変換"""
    func_name = node.name
    args_list = []
    for arg in node.args.args:
        arg_name = arg.arg
        arg_type = translate_type(arg.annotation)
        args_list.append(f"({arg_name} : {arg_type})")
    args = " ".join(args_list)
    return_type = translate_type(node.returns)
    # body[0] は return 文などを想定
    body = translate_to_lean(node.body[0])
    return f"def {func_name} {args} : {return_type} :=\n  {body}"

def _translate_constant(node):
    """ast.Constant をLeanのリテラルに変換"""
    if isinstance(node.value, str):
        return f'"{node.value}"'
    return str(node.value)

def _translate_name(node):
    """ast.Name をLeanの識別子に変換"""
    return node.id

def _translate_return(node):
    """ast.Return の中身を変換"""
    return translate_to_lean(node.value)

def _translate_expr(node):
    """ast.Expr の中身を変換"""
    return translate_to_lean(node.value)

def _translate_bin_op(node):
    """ast.BinOp をLeanの二項演算に変換"""
    left = translate_to_lean(node.left)
    right = translate_to_lean(node.right)
    op_map = {
        ast.Add: "+", ast.Sub: "-", ast.Mult: "*",
        ast.Div: "/", ast.FloorDiv: "/", ast.Mod: "%",
    }
    op_symbol = op_map.get(type(node.op))
    if op_symbol:
        return f"({left} {op_symbol} {right})"
    return "/* サポート外の二項演算子 */"

def _translate_if_exp(node):
    """ast.IfExp (三項演算子) をLeanのif式に変換"""
    test = translate_to_lean(node.test)
    body = translate_to_lean(node.body)
    orelse = translate_to_lean(node.orelse)
    return f"if {test} then {body} else {orelse}"

def _translate_if(node):
    """ast.If をLeanのif式に変換"""
    test = translate_to_lean(node.test)
    body = translate_to_lean(node.body[0])
    orelse = translate_to_lean(node.orelse[0]) if node.orelse else "0"
    return f"if {test} then {body} else {orelse}"

def _translate_compare(node):
    """ast.Compare をLeanの比較演算に変換"""
    left = translate_to_lean(node.left)
    # NOTE: 複数の比較演算子には未対応
    op = "≠" if isinstance(node.ops[0], ast.NotEq) else "=="
    right = translate_to_lean(node.comparators[0])
    return f"{left} {op} {right}"

# --- 変換ロジックのメインディスパッチャ ---
def translate_to_lean(node):
    """ASTノードを解析し、対応する変換関数を呼び出す"""
    if node is None:
        return ""

    if isinstance(node, ast.FunctionDef): return _translate_function_def(node)
    elif isinstance(node, ast.Constant): return _translate_constant(node)
    elif isinstance(node, ast.Name): return _translate_name(node)
    elif isinstance(node, ast.Return): return _translate_return(node)
    elif isinstance(node, ast.Expr): return _translate_expr(node)
    elif isinstance(node, ast.BinOp): return _translate_bin_op(node)
    elif isinstance(node, ast.IfExp): return _translate_if_exp(node)
    elif isinstance(node, ast.If): return _translate_if(node)
    elif isinstance(node, ast.Compare): return _translate_compare(node)
    
    return "/* サポート外 */"