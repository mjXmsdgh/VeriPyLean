import ast
import fractions
from . import types
from typing import Tuple, Optional

def translate_to_lean(node):
    """ASTノードを解析し、対応する変換を呼び出す (Entry Point)"""
    if node is None: return ""
    return LeanTranslator().visit(node)

class LeanTranslator(ast.NodeVisitor):
    """ASTを巡回してLeanコードを生成するビジター"""
    def generic_visit(self, node): return "/* サポート外 */"

    def _extract_doc_and_body(self, node):
        """ノードからdocstringを除去した本体ステートメントを返す"""
        doc = ast.get_docstring(node)
        stmts = node.body
        # docstringが最初の式として存在する場合、bodyから除外
        if doc and stmts and isinstance(stmts[0], ast.Expr):
            stmts = stmts[1:]
        return doc, stmts

    def _format_args(self, args_node):
        """関数引数を (name : Type) の形式で結合する"""
        return " ".join([f"({a.arg} : {types.translate_type(a.annotation)})" for a in args_node.args])

    def _wrap_if_complex(self, arg_node):
        """結合順序が紛らわしい式（CallやIfExp）を括弧で囲む"""
        lean_str = translate_to_lean(arg_node)
        if isinstance(arg_node, (ast.Call, ast.IfExp)):
            return f"({lean_str})"
        return lean_str

    def visit_FunctionDef(self, node):
        doc, stmts = self._extract_doc_and_body(node)
        args = self._format_args(node.args)
        is_thm = node.name.startswith(("verify_", "theorem_"))
        
        # 本体の変換
        body_lines = [translate_to_lean(s) for s in stmts] or ["sorry"]
        doc_prefix = f"/-- {doc} -/\n" if doc else ""

        if is_thm:
            # 定理(theorem)の場合は最後のReturnを命題として扱う
            is_ret = isinstance(stmts[-1], ast.Return)
            prop = translate_to_lean(stmts[-1].value) if is_ret else "True"
            if is_ret: body_lines = body_lines[:-1]
            res = f"{doc_prefix}theorem {node.name} {args} : {prop} :=\n  " + "\n  ".join(body_lines + ["by sorry"])
        else:
            res = f"{doc_prefix}def {node.name} {args} : {types.translate_type(node.returns)} :=\n  " + "\n  ".join(body_lines)

        # 再帰解析の統合
        is_rec, hint = _analyze_recursion(node)
        if is_rec:
            res += f"\ntermination_by {hint}" if hint else ""
            if not hint: res = f"-- [PyLean] Warning: No termination measure found.\n{res}"
        return res
    def visit_ClassDef(self, node):
        is_enum = any(isinstance(b, ast.Name) and b.id == "Enum" for b in node.bases)
        is_dc = any((isinstance(d, ast.Name) and d.id == "dataclass") or (isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "dataclass") for d in node.decorator_list)
        if is_enum:
            vars = [f"  | {t.id}" for s in node.body if isinstance(s, ast.Assign) for t in s.targets if isinstance(t, ast.Name)]
            return f"inductive {node.name} where\n" + "\n".join(vars) + "\nderiving Repr, BEq"
        elif is_dc:
            fields = [f"  {s.target.id} : {types.translate_type(s.annotation)}" for s in node.body if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name)]
            return f"structure {node.name} where\n" + "\n".join(fields) + "\nderiving Repr, BEq"
        return "/* サポート外のクラス定義 */"

    def visit_Assign(self, node): return f"let {translate_to_lean(node.targets[0])} := {translate_to_lean(node.value)};"
    def visit_Constant(self, node): return f'"{node.value}"' if isinstance(node.value, str) else str(node.value)
    def visit_Name(self, node): return node.id
    def visit_Attribute(self, node): return f"{translate_to_lean(node.value)}.{node.attr}"
    def visit_Return(self, node): return translate_to_lean(node.value)
    def visit_Assert(self, node): return f"have : {translate_to_lean(node.test)} := by sorry"
    def visit_Expr(self, node): return translate_to_lean(node.value)
    def visit_BinOp(self, node):
        l, r = translate_to_lean(node.left), translate_to_lean(node.right)
        if isinstance(node.op, ast.Div): return f"(py_div ({l}) ({r}))"
        op_m = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.FloorDiv: "/", ast.Mod: "%", ast.Pow: "^"}
        return f"({l} {op_m[type(node.op)]} {r})" if type(node.op) in op_m else "/* サポート外 */"
    def visit_IfExp(self, node): return f"if {translate_to_lean(node.test)} then {translate_to_lean(node.body)} else {translate_to_lean(node.orelse)}"
    def visit_If(self, node):
        orelse = translate_to_lean(node.orelse[0]) if node.orelse else "0"
        return f"if {translate_to_lean(node.test)} then {translate_to_lean(node.body[0])} else {orelse}"
    def visit_BoolOp(self, node):
        op = "&&" if isinstance(node.op, ast.And) else "||"
        return f"({' ' + op + ' '.join([translate_to_lean(v) for v in node.values])})"
    def visit_UnaryOp(self, node): return f"(!{translate_to_lean(node.operand)})" if isinstance(node.op, ast.Not) else "/* サポート外 */"
    def visit_Compare(self, node):
        op_m = {ast.Eq: "==", ast.NotEq: "≠", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">="}
        parts, curr = [], translate_to_lean(node.left)
        for op, comp in zip(node.ops, node.comparators):
            next_v = translate_to_lean(comp)
            parts.append(f"({curr} {op_m.get(type(op), '?')} {next_v})")
            curr = next_v
        return parts[0] if len(parts) == 1 else f"({' && '.join(parts)})"
    def visit_List(self, node): return f"[{', '.join([translate_to_lean(e) for e in node.elts])}]"
    def visit_Tuple(self, node): return f"({', '.join([translate_to_lean(e) for e in node.elts])})"

    def visit_Call(self, node):
        fn = translate_to_lean(node.func)
        h = _BUILTIN_CALL_HANDLERS.get(fn) or (isinstance(node.func, ast.Attribute) and _METHOD_CALL_HANDLERS.get(node.func.attr))
        if h:
            res = h(node)
            if res: return res
        args = [self._wrap_if_complex(a) for a in node.args]
        return fn if not args else f"{fn} {' '.join(args)}"

    def visit_ListComp(self, node):
        def build(gens, elt):
            if not gens: return translate_to_lean(elt)
            g, inner = gens[0], build(gens[1:], elt)
            t, i = translate_to_lean(g.target), translate_to_lean(g.iter)
            if not g.ifs: return f"({i}).map (fun {t} => {inner})" if len(gens) == 1 else f"({i}).flatMap (fun {t} => {inner})"
            c = " && ".join(f"({translate_to_lean(cond)})" for cond in g.ifs)
            return f"({i}).filterMap (fun {t} => if {c} then some ({inner}) else none)" if len(gens) == 1 else f"({i}).filter (fun {t} => {c}).flatMap (fun {t} => {inner})"
        return build(node.generators, node.elt)

    def visit_For(self, node): return "/* for ループは現在サポート外。 */"

# --- ビルトイン関数・メソッド変換用レジストリ ---

def _handle_decimal_call(node):
    if len(node.args) == 1 and isinstance(node.args[0], ast.Constant):
        try:
            f = fractions.Fraction(node.args[0].value)
            return f"({f.numerator}/{f.denominator} : Rat)"
        except Exception: pass
    return None

def _handle_unary_call(lean_func):
    return lambda node: f"({lean_func} {translate_to_lean(node.args[0])})" if len(node.args) == 1 else None

def _handle_min_max_call(node):
    func_name = translate_to_lean(node.func)
    if len(node.args) >= 2:
        args_str = [translate_to_lean(arg) for arg in node.args]
        result = args_str[-1]
        for arg in reversed(args_str[:-1]):
            result = f"({func_name} {arg} {result})"
        return result
    return None

def _handle_date_call(node):
    if len(node.args) == 3:
        a = [translate_to_lean(arg) for arg in node.args]
        return f"({{ year := {a[0]}, month := {a[1]}, day := {a[2]} }} : Date)"
    return None

def _handle_quantize_method(node):
    target = translate_to_lean(node.func.value)
    is_half_up = any(kw.arg == "rounding" and isinstance(kw.value, ast.Name) and kw.value.id == "ROUND_HALF_UP" for kw in node.keywords)
    return f"(py_round_half_up {target})" if is_half_up else None

_BUILTIN_CALL_HANDLERS = {
    "Decimal": _handle_decimal_call, "decimal.Decimal": _handle_decimal_call,
    "math.ceil": _handle_unary_call("py_ceil"), "ceil": _handle_unary_call("py_ceil"),
    "math.floor": _handle_unary_call("py_floor"), "floor": _handle_unary_call("py_floor"),
    "round": _handle_unary_call("py_round"),
    "sum": _handle_unary_call("py_sum"),
    "len": _handle_unary_call("List.length"),
    "min": _handle_min_max_call, "max": _handle_min_max_call,
    "date": _handle_date_call, "datetime.date": _handle_date_call,
}

_METHOD_CALL_HANDLERS = {
    "quantize": _handle_quantize_method,
}

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