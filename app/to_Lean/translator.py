import ast
import fractions
from . import types
from typing import Tuple, Optional

# --- 各ASTノードに対応する変換関数 ---

def _translate_function_def(node):
    """ast.FunctionDef をLeanの関数定義に変換"""
    func_name = node.name
    
    # Docstringの取得と処理
    docstring = ast.get_docstring(node)
    doc_comment = ""
    stmts = node.body

    if docstring:
        # Leanのドキュメントコメント形式に変換
        doc_comment = f"/-- {docstring} -/\n"
        # docstring文をbodyの変換対象から除外（先頭の文字列リテラル式をスキップ）
        if len(stmts) > 0 and isinstance(stmts[0], ast.Expr) and \
           isinstance(stmts[0].value, ast.Constant) and \
           isinstance(stmts[0].value.value, str):
            stmts = stmts[1:]

    args_list = []
    for arg in node.args.args:
        arg_name = arg.arg
        arg_type = types.translate_type(arg.annotation)
        args_list.append(f"({arg_name} : {arg_type})")
    args = " ".join(args_list)
    return_type = types.translate_type(node.returns)

    # 定理化の判定: verify_ または theorem_ で始まる関数は theorem として扱う
    is_theorem = func_name.startswith("verify_") or func_name.startswith("theorem_")
    keyword = "theorem" if is_theorem else "def"

    # 関数本体のステートメントを変換
    body_lines = [translate_to_lean(stmt) for stmt in stmts]

    # 本体が空の場合（docstringのみの場合など）のフォールバック
    if not body_lines:
        body_lines = ["sorry"]

    if is_theorem:
        # 定理の場合、最後の return 式を命題 (Type) とし、本体を証明 (by sorry) にする
        prop_expr = "True"
        if isinstance(stmts[-1], ast.Return):
            prop_expr = translate_to_lean(stmts[-1].value)
            body_lines = body_lines[:-1]
        
        body = "\n  ".join(body_lines + ["by sorry"])
        func_def_string = f"{doc_comment}{keyword} {func_name} {args} : {prop_expr} :=\n  {body}"
    else:
        body = "\n  ".join(body_lines)
        # 基本の関数定義文字列を作成
        func_def_string = f"{doc_comment}{keyword} {func_name} {args} : {return_type} :=\n  {body}"

    # 再帰を解析し、必要なら termination_by や警告コメントを追加
    is_recursive, termination_hint = _analyze_recursion(node)
    if is_recursive:
        if termination_hint:
            func_def_string += f"\ntermination_by {termination_hint}"
        else:
            comment = "-- [PyLean] Warning: Could not automatically determine termination measure. A 'termination_by' clause may be required."
            func_def_string = f"{comment}\n{func_def_string}"

    return func_def_string

def _translate_class_def(node):
    """ast.ClassDef をLeanの型定義に変換"""
    # Enum (列挙型) の判定
    is_enum = any(isinstance(base, ast.Name) and base.id == "Enum" for base in node.bases)
    
    # dataclass の判定 (@dataclass または @dataclass(...))
    is_dataclass = any(
        (isinstance(dec, ast.Name) and dec.id == "dataclass") or
        (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) and dec.func.id == "dataclass")
        for dec in node.decorator_list
    )
    
    if is_enum:
        enum_name = node.name
        variants = []
        for stmt in node.body:
            # Docstringのスキップ
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                continue
            
            # 変数割り当て（Enumの各要素）を抽出
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        variants.append(f"  | {target.id}")
        
        variants_str = "\n".join(variants)
        return f"inductive {enum_name} where\n{variants_str}\nderiving Repr, BEq"

    elif is_dataclass:
        struct_name = node.name
        fields = []
        for stmt in node.body:
            # Docstringのスキップ
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                continue
            
            # 型注釈付きのフィールド定義 (AnnAssign) を抽出
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                field_name = stmt.target.id
                field_type = types.translate_type(stmt.annotation)
                fields.append(f"  {field_name} : {field_type}")
        
        fields_str = "\n".join(fields)
        return f"structure {struct_name} where\n{fields_str}\nderiving Repr, BEq"
    
    return "/* サポート外のクラス定義です（現在はEnumのみサポート） */"

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

def _translate_assert(node):
    """ast.Assert をLeanの have 文に変換"""
    test = translate_to_lean(node.test)
    return f"have : {test} := by sorry"

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
        ast.FloorDiv: "/", ast.Mod: "%", ast.Pow: "^",
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

    # 丸め関数 (round, ceil, floor) の対応
    if func_name in ("math.ceil", "ceil"):
        if len(node.args) == 1:
            return f"(py_ceil {translate_to_lean(node.args[0])})"

    if func_name in ("math.floor", "floor"):
        if len(node.args) == 1:
            return f"(py_floor {translate_to_lean(node.args[0])})"

    if func_name == "round":
        if len(node.args) == 1:
            return f"(py_round {translate_to_lean(node.args[0])})"

    # Decimal.quantize(..., rounding=ROUND_HALF_UP) の簡易対応
    if isinstance(node.func, ast.Attribute) and node.func.attr == "quantize":
        target = translate_to_lean(node.func.value)
        # キーワード引数 rounding をチェック
        is_half_up = any(kw.arg == "rounding" and isinstance(kw.value, ast.Name) and kw.value.id == "ROUND_HALF_UP" for kw in node.keywords)
        if is_half_up:
            return f"(py_round_half_up {target})"
            
    # List built-ins
    if func_name == "sum":
        if len(node.args) == 1:
            return f"(py_sum {translate_to_lean(node.args[0])})"
    
    if func_name == "len":
        if len(node.args) == 1:
            return f"(List.length {translate_to_lean(node.args[0])})"

    # min, max の可変長引数対応 (例: min(a, b, c) -> min a (min b c))
    if func_name in ("min", "max"):
        if len(node.args) >= 2:
            args_str = [translate_to_lean(arg) for arg in node.args]
            # 後ろから再帰的に畳み込む
            result = args_str[-1]
            for arg in reversed(args_str[:-1]):
                result = f"({func_name} {arg} {result})"
            return result

    # Date constructor
    if func_name in ("date", "datetime.date"):
        if len(node.args) == 3:
            args_str = [translate_to_lean(arg) for arg in node.args]
            return f"({{ year := {args_str[0]}, month := {args_str[1]}, day := {args_str[2]} }} : Date)"

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

def _translate_list_comp(node):
    """ast.ListComp をLeanの List.flatMap/map/filterMap に再帰的に変換"""
    def build_comp(gens, elt_lean):
        if not gens:
            return elt_lean
        
        gen = gens[0]
        target = translate_to_lean(gen.target)
        iter_val = translate_to_lean(gen.iter)
        inner_lean = build_comp(gens[1:], elt_lean)
        
        if not gen.ifs:
            if len(gens) == 1:
                return f"({iter_val}).map (fun {target} => {inner_lean})"
            else:
                return f"({iter_val}).flatMap (fun {target} => {inner_lean})"
        else:
            conds = [translate_to_lean(c) for c in gen.ifs]
            full_cond = " && ".join(f"({c})" for c in conds)
            if len(gens) == 1:
                return f"({iter_val}).filterMap (fun {target} => if {full_cond} then some ({inner_lean}) else none)"
            else:
                # 途中のジェネレータに条件がある場合は filter してから flatMap
                return f"({iter_val}).filter (fun {target} => {full_cond}).flatMap (fun {target} => {inner_lean})"

    return build_comp(node.generators, translate_to_lean(node.elt))

def _translate_for(node):
    """ast.For は現在サポート外であることを示すコメントを返す"""
    return "/* for ループは List.map, List.foldl, または再帰関数への変換が必要なため、現在直接の変換はサポートされていません。リスト内包表記や sum() などの高階関数の使用を検討してください。 */"

# --- 変換ロジックのメインディスパッチャ ---
def translate_to_lean(node):
    """ASTノードを解析し、対応する変換関数を呼び出す"""
    if node is None:
        return ""

    if isinstance(node, ast.FunctionDef): return _translate_function_def(node)
    elif isinstance(node, ast.ClassDef): return _translate_class_def(node)
    elif isinstance(node, ast.Assign): return _translate_assign(node)
    elif isinstance(node, ast.Constant): return _translate_constant(node)
    elif isinstance(node, ast.Name): return _translate_name(node)
    elif isinstance(node, ast.Attribute): return _translate_attribute(node)
    elif isinstance(node, ast.Return): return _translate_return(node)
    elif isinstance(node, ast.Assert): return _translate_assert(node)
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
    elif isinstance(node, ast.ListComp): return _translate_list_comp(node)
    elif isinstance(node, ast.For): return _translate_for(node)
    
    return "/* サポート外 */"

def _analyze_recursion(func_def_node: ast.FunctionDef) -> Tuple[bool, Optional[str]]:
    """
    関数定義ASTを解析し、再帰呼び出しの有無と停止性のヒントを返す。
    戻り値: (is_recursive: bool, hint: str | None)
    """
    func_name = func_def_node.name
    
    class RecursionVisitor(ast.NodeVisitor):
        def __init__(self):
            self.is_recursive = False
            self.hint: Optional[str] = None

        def visit_Call(self, node: ast.Call):
            # 自分自身を呼び出しているか？
            if isinstance(node.func, ast.Name) and node.func.id == func_name:
                self.is_recursive = True
                
                # 既にヒントを見つけていれば何もしない
                if self.hint:
                    self.generic_visit(node)
                    return

                # 引数と元の引数名を対応付ける
                for i, arg_node in enumerate(node.args):
                    if i < len(func_def_node.args.args):
                        param_name = func_def_node.args.args[i].arg
                        
                        # 引数が `param - C` (Cは正の整数) の形かチェック
                        if (isinstance(arg_node, ast.BinOp) and
                            isinstance(arg_node.left, ast.Name) and
                            arg_node.left.id == param_name and
                            isinstance(arg_node.op, ast.Sub) and
                            isinstance(arg_node.right, ast.Constant) and
                            isinstance(arg_node.right.value, int) and
                            arg_node.right.value > 0):
                            
                            self.hint = param_name
            
            self.generic_visit(node)

    visitor = RecursionVisitor()
    visitor.visit(func_def_node)
    return visitor.is_recursive, visitor.hint