import ast
import fractions

# --- 型変換のヘルパー関数 ---
def translate_type(annotation_node):
    """Pythonの型ヒントASTノードをLeanの型文字列に変換する"""
    if annotation_node is None:
        return "Int"  # 型ヒントがない場合のデフォルト

    # 単純な名前 (int, str, List など)
    if isinstance(annotation_node, ast.Name):
        type_map = {
            'int': 'Int',
            'str': 'String',
            'bool': 'Bool',
            'float': 'Float',
            'list': 'List Int', # 具象型指定がない場合
            'Decimal': 'Rat',
            'List': 'List Int'
        }
        return type_map.get(annotation_node.id, "Int")  # マップにない場合はIntにフォールバック

    # 構造化された型 (List[int] など)
    if isinstance(annotation_node, ast.Subscript):
        # valueが List かどうか確認
        container = translate_type(annotation_node.value)
        # 内部の型 (int など) を再帰的に取得
        inner_type = translate_type(annotation_node.slice)
        
        if "List" in container:
            return f"List {inner_type}"
            
    # モジュール属性 (decimal.Decimal など)
    if isinstance(annotation_node, ast.Attribute):
        if annotation_node.attr == 'Decimal':
            return 'Rat'

    return "Int"

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
    # 関数本体のステートメントを変換
    body_lines = [translate_to_lean(stmt) for stmt in node.body]
    body = "\n  ".join(body_lines)
    return f"def {func_name} {args} : {return_type} :=\n  {body}"

def _translate_list(node):
    """ast.List をLeanのリテラルに変換"""
    elements = [translate_to_lean(el) for el in node.elts]
    return f"[{', '.join(elements)}]"

def _translate_tuple(node):
    """ast.Tuple をLeanのタプルに変換"""
    elements = [translate_to_lean(el) for el in node.elts]
    return f"({', '.join(elements)})"

def _translate_constant(node):
    """ast.Constant をLeanのリテラルに変換"""
    if isinstance(node.value, str):
        return f'"{node.value}"'
    return str(node.value)

def _translate_name(node):
    """ast.Name をLeanの識別子に変換"""
    return node.id

def _translate_attribute(node):
    """ast.Attribute をLeanのドット記法に変換"""
    value = translate_to_lean(node.value)
    return f"{value}.{node.attr}"

def _translate_assign(node):
    """ast.Assign をLeanのlet定義に変換"""
    target = translate_to_lean(node.targets[0])
    value = translate_to_lean(node.value)
    return f"let {target} := {value};"

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
    
    # Pythonの / (Div) は型に応じて挙動が変わるため、ヘルパー関数 py_div を使用する
    if isinstance(node.op, ast.Div):
        return f"(py_div ({left}) ({right}))"

    op_map = {
        ast.Add: "+", ast.Sub: "-", ast.Mult: "*",
        ast.FloorDiv: "/", ast.Mod: "%",
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

def _translate_bool_op(node):
    """ast.BoolOp をLeanの論理演算に変換 (and, or)"""
    op_map = {ast.And: "&&", ast.Or: "||"}
    op_symbol = op_map.get(type(node.op))
    if not op_symbol:
        return "/* サポート外の論理演算子 */"
    
    values = [translate_to_lean(v) for v in node.values]
    return f"({f' {op_symbol} '.join(values)})"

def _translate_unary_op(node):
    """ast.UnaryOp をLeanの単項演算に変換 (not)"""
    operand = translate_to_lean(node.operand)
    if isinstance(node.op, ast.Not):
        return f"(!{operand})"
    return "/* サポート外の単項演算子 */"

def _translate_compare(node):
    """ast.Compare をLeanの比較演算に変換"""
    op_map = {
        ast.Eq: "==", ast.NotEq: "≠", ast.Lt: "<",
        ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=",
    }
    
    parts = []
    current_left = translate_to_lean(node.left)
    
    for op, comparator in zip(node.ops, node.comparators):
        current_right = translate_to_lean(comparator)
        op_symbol = op_map.get(type(op), "/* ? */")
        parts.append(f"({current_left} {op_symbol} {current_right})")
        current_left = current_right
        
    if len(parts) == 1:
        return parts[0]
    
    return f"({' && '.join(parts)})"

def _translate_call(node):
    """ast.Call をLeanの関数適用に変換"""
    func_name = translate_to_lean(node.func)
    
    # Decimalのコンストラクタ呼び出しを特別扱いして Rat に変換
    if func_name == "Decimal" or func_name == "decimal.Decimal":
        if len(node.args) == 1:
            arg = node.args[0]
            # 文字列または数値リテラルの場合、正確な有理数に変換
            if isinstance(arg, ast.Constant):
                try:
                    val = arg.value
                    # 文字列または数値からFractionを作成
                    f = fractions.Fraction(val)
                    return f"({f.numerator}/{f.denominator} : Rat)"
                except Exception:
                    pass

    args = []
    for arg in node.args:
        arg_str = translate_to_lean(arg)
        # 引数が関数呼び出しやif式の場合は括弧で囲む
        if isinstance(arg, (ast.Call, ast.IfExp)):
            arg_str = f"({arg_str})"
        args.append(arg_str)
    
    if not args:
        return func_name
    return f"{func_name} {' '.join(args)}"

# --- 変換ロジックのメインディスパッチャ ---
def translate_to_lean(node):
    """ASTノードを解析し、対応する変換関数を呼び出す"""
    if node is None:
        return ""

    if isinstance(node, ast.FunctionDef): return _translate_function_def(node)
    elif isinstance(node, ast.Assign): return _translate_assign(node)
    elif isinstance(node, ast.Constant): return _translate_constant(node)
    elif isinstance(node, ast.Name): return _translate_name(node)
    elif isinstance(node, ast.Attribute): return _translate_attribute(node)
    elif isinstance(node, ast.Return): return _translate_return(node)
    elif isinstance(node, ast.Expr): return _translate_expr(node)
    elif isinstance(node, ast.BinOp): return _translate_bin_op(node)
    elif isinstance(node, ast.IfExp): return _translate_if_exp(node)
    elif isinstance(node, ast.If): return _translate_if(node)
    elif isinstance(node, ast.BoolOp): return _translate_bool_op(node)
    elif isinstance(node, ast.UnaryOp): return _translate_unary_op(node)
    elif isinstance(node, ast.Compare): return _translate_compare(node)
    elif isinstance(node, ast.List): return _translate_list(node)
    elif isinstance(node, ast.Tuple): return _translate_tuple(node)
    elif isinstance(node, ast.Call): return _translate_call(node)
    
    return "/* サポート外 */"

def _generate_preamble(lean_code):
    """Leanコードの内容に基づいて必要なヘルパー定義（プリアンブル）を生成する"""
    preamble_parts = []

    # 文字列結合 (+) のサポート
    if "String" in lean_code or '"' in lean_code:
        preamble_parts.append("instance : Add String where add := String.append")
    
    # Float除算のための Int -> Float 自動型変換サポート
    if "Float" in lean_code:
        preamble_parts.append("instance : Coe Int Float where coe := Int.toFloat")

    # 除算 (/) のためのヘルパー型クラス定義
    preamble_parts.append("""class PyDiv (α : Type) (β : outParam Type) where
  py_div : α -> α -> β

instance : PyDiv Int Float where py_div a b := (a : Float) / (b : Float)
instance : PyDiv Float Float where py_div a b := a / b
instance : PyDiv Rat Rat where py_div a b := a / b""")

    return "\n\n".join(preamble_parts) + ("\n\n" if preamble_parts else "")

def compile_python_to_lean(code_input):
    """Pythonコード文字列を受け取り、完全なLeanコード文字列を返す"""
    try:
        parsed_ast_root = ast.parse(code_input)
    except SyntaxError as e:
        raise ValueError(f"構文エラー: {e}")

    if not parsed_ast_root.body:
        raise ValueError("コードが入力されていません。")
    
    parsed_ast = parsed_ast_root.body[0]
    
    # Lean風のテキストに変換
    lean_code = translate_to_lean(parsed_ast)
    
    # 必要なヘルパー定義（プリアンブル）を構築
    preamble = _generate_preamble(lean_code)

    # トップレベルのノードが関数定義なら、変換結果をそのまま使う
    # そうでなければ、ダミーの関数(example)でラップしてLeanの構文に合わせる
    if isinstance(parsed_ast, ast.FunctionDef):
        return preamble + lean_code
    else:
        return preamble + f"def example (n : Int) : Int :=\n  {lean_code}"