import ast
import fractions
from . import types
from contextlib import contextmanager
from typing import Tuple, Optional

def translate_to_lean(node, context=None):
    """ASTノードを解析し、対応する変換を呼び出す (Entry Point)"""
    if node is None: return ""
    if context is None:
        # 個別ノードの変換でも最小限の解析を行う
        context = analyze(node)
    return LeanTranslator(context).visit(node)

def analyze(node):
    """ASTを解析して変換に必要なメタデータを作成する"""
    context = TranslationContext()
    AnalysisVisitor(context).visit(node)
    return context

# --- 宣言的なマッピングの定義 ---

BIN_OPS = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.FloorDiv: "/",
    ast.Mod: "%",
    ast.Pow: "^",
}

COMP_OPS = {
    ast.Eq: "==",
    ast.NotEq: "≠",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
}

BOOL_OPS = {
    ast.And: "&&",
    ast.Or: "||",
}

UNARY_OPS = {
    ast.Not: "!",
    ast.USub: "-",
}

# --- テンプレート定義 ---

IND_TEMPLATE = """inductive {name} where
{items}
deriving Repr, BEq"""

STRUCT_TEMPLATE = """structure {name} where
{items}
deriving Repr, BEq"""

# --- コードビルダー ---

class CodeBuilder:
    def __init__(self, indent_size=2):
        self.lines = []
        self.level = 0
        self.indent_size = indent_size

    def indent(self): self.level += 1
    def dedent(self): self.level = max(0, self.level - 1)

    def add(self, text):
        prefix = " " * (self.level * self.indent_size)
        self.lines.append(f"{prefix}{text}")

    @contextmanager
    def block(self, header):
        self.add(header)
        self.indent()
        yield
        self.dedent()

    def build(self): return "\n".join(self.lines)

class TranslationContext:
    """変換中に参照されるメタデータ情報を保持する"""
    def __init__(self):
        self.functions = {}  # name -> {"is_recursive": bool, "hint": str}
        self.classes = {}    # name -> "enum" | "structure"
        self.warnings = []

    def add_warning(self, node, message):
        line = getattr(node, 'lineno', 'unknown')
        self.warnings.append(f"Line {line}: {message}")

class AnalysisVisitor(ast.NodeVisitor):
    """生成前にASTを走査して情報を収集する"""
    def __init__(self, context):
        self.context = context

    def visit_ClassDef(self, node):
        is_enum = any(isinstance(b, ast.Name) and b.id == "Enum" for b in node.bases)
        is_dc = any((isinstance(d, ast.Name) and d.id == "dataclass") or 
                    (isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "dataclass") 
                    for d in node.decorator_list)
        if is_enum: self.context.classes[node.name] = "enum"
        elif is_dc: self.context.classes[node.name] = "structure"
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # 再帰解析
        is_rec, hint = self._check_recursion(node)
        self.context.functions[node.name] = {"is_recursive": is_rec, "hint": hint}
        self.generic_visit(node)

    def _check_recursion(self, func_node):
        """関数内の再帰呼び出しを判定する"""
        func_name = func_node.name
        res = {"is_recursive": False, "hint": None}
        
        class RecursionChecker(ast.NodeVisitor):
            def visit_Call(self, call_node):
                if isinstance(call_node.func, ast.Name) and call_node.func.id == func_name:
                    res["is_recursive"] = True
                    # 停止性ヒントの簡易抽出 (n - 1 などのパターン)
                    for i, arg in enumerate(call_node.args):
                        if (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub) and 
                            isinstance(arg.left, ast.Name) and i < len(func_node.args.args) and
                            arg.left.id == func_node.args.args[i].arg):
                            res["hint"] = arg.left.id
                self.generic_visit(call_node)
        
        RecursionChecker().visit(func_node)
        return res["is_recursive"], res["hint"]

class LeanTranslator(ast.NodeVisitor):
    """ASTを巡回してLeanコードを生成するビジター"""
    def __init__(self, context):
        self.context = context

    def generic_visit(self, node):
        """未知のノードに対するデフォルトのフォールバック"""
        return self._unsupported(node)

    def _v(self, node):
        """再帰的な変換のヘルパー"""
        if node is None: return ""
        return self.visit(node)

    def _unsupported(self, node, detail=None):
        """サポート外の機能に遭遇した際の共通処理"""
        node_type = type(node).__name__
        msg = f"Python feature '{node_type}' is not supported yet"
        if detail: msg += f" ({detail})"
        self.context.add_warning(node, msg)
        return f"/- {msg} -/ sorry"

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

    def _wrap(self, node, trigger_types=(ast.Call, ast.IfExp, ast.BinOp, ast.Compare)):
        """必要に応じて式を括弧で囲む"""
        res = self._v(node)
        if isinstance(node, trigger_types):
            return f"({res})"
        return res

    def visit_FunctionDef(self, node):
        doc, stmts = self._extract_doc_and_body(node)
        args = self._format_args(node.args)
        is_thm = node.name.startswith(("verify_", "theorem_"))
        meta = self.context.functions.get(node.name, {})
        return self._build_function_or_theorem(node, doc, stmts, args, is_thm, meta)

    def visit_ClassDef(self, node):
        """クラス定義をEnumまたはStructure(Dataclass)として変換する"""
        kind = self.context.classes.get(node.name)
        if kind == "enum":
            return self._translate_enum(node)
        if kind == "structure":
            return self._translate_structure(node)
        return self._unsupported(node, "Only Enums and @dataclass are supported")

    def visit_Assign(self, node): return f"let {self._v(node.targets[0])} := {self._v(node.value)};"
    def visit_Constant(self, node): return f'"{node.value}"' if isinstance(node.value, str) else str(node.value)
    def visit_Name(self, node): return node.id
    def visit_Attribute(self, node): return f"{self._v(node.value)}.{node.attr}"
    def visit_Return(self, node): return self._v(node.value)
    def visit_Assert(self, node): return f"have : {self._v(node.test)} := by sorry"
    def visit_Expr(self, node): return self._v(node.value)
    def visit_BinOp(self, node):
        l, r = self._v(node.left), self._v(node.right)
        if isinstance(node.op, ast.Div): return f"(py_div ({l}) ({r}))"
        op = BIN_OPS.get(type(node.op))
        return f"({l} {op} {r})" if op else self._unsupported(node.op)
    def visit_IfExp(self, node): return f"if {self._v(node.test)} then {self._v(node.body)} else {self._v(node.orelse)}"
    def visit_If(self, node):
        orelse = self._v(node.orelse[0]) if node.orelse else "0"
        return f"if {self._v(node.test)} then {self._v(node.body[0])} else {orelse}"
    def visit_BoolOp(self, node):
        op = BOOL_OPS.get(type(node.op), "??")
        return f"({(f' {op} ').join([self._v(v) for v in node.values])})"
    def visit_UnaryOp(self, node):
        op = UNARY_OPS.get(type(node.op))
        return f"({op}{self._v(node.operand)})" if op else self._unsupported(node.op)
    def visit_Compare(self, node):
        parts, curr = [], self._v(node.left)
        for op, comp in zip(node.ops, node.comparators):
            next_v = self._v(comp)
            parts.append(f"({curr} {COMP_OPS.get(type(op), '?')} {next_v})")
            curr = next_v
        return parts[0] if len(parts) == 1 else f"({' && '.join(parts)})"
    def visit_List(self, node): return f"[{', '.join([self._v(e) for e in node.elts])}]"
    def visit_Tuple(self, node): return f"({', '.join([self._v(e) for e in node.elts])})"

    def visit_Call(self, node):
        fn = self._v(node.func)
        h = _BUILTIN_CALL_HANDLERS.get(fn) or (isinstance(node.func, ast.Attribute) and _METHOD_CALL_HANDLERS.get(node.func.attr))
        if h:
            res = h(node, self)
            if res: return res
        args = [self._wrap(a, trigger_types=(ast.IfExp, ast.BinOp)) for a in node.args]
        return fn if not args else f"{fn} {' '.join(args)}"

    def visit_ListComp(self, node):
        return self._translate_list_comp_recursive(node.generators, node.elt)

    def visit_For(self, node): return "-- [PyLean] Error: for loops are not supported. Use list comprehensions or recursion."

    # --- 複雑な変換ロジックの内部ヘルパー ---

    def _translate_enum(self, node):
        """PythonのEnumをLeanのinductive型に変換"""
        variants = [f"  | {t.id}" for s in node.body if isinstance(s, ast.Assign) 
                    for t in s.targets if isinstance(t, ast.Name)]
        return IND_TEMPLATE.format(name=node.name, items="\n".join(variants))

    def _translate_structure(self, node):
        """PythonのdataclassをLeanのstructureに変換"""
        fields = [f"  {s.target.id} : {types.translate_type(s.annotation)}" 
                  for s in node.body if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name)]
        return STRUCT_TEMPLATE.format(name=node.name, items="\n".join(fields))

    def _translate_list_comp_recursive(self, generators, elt):
        """リスト内包表記をLeanのmap/flatMap/filterMapチェーンに再帰的に変換"""
        if not generators:
            return self._v(elt)
        
        gen, *rest = generators
        inner = self._translate_list_comp_recursive(rest, elt)
        target = self._v(gen.target)
        iterable = self._v(gen.iter)
        
        if not gen.ifs:
            method = "map" if not rest else "flatMap"
            return f"({iterable}).{method} (fun {target} => {inner})"
        
        cond = " && ".join(f"({self._v(c)})" for c in gen.ifs)
        if not rest:
            return f"({iterable}).filterMap (fun {target} => if {cond} then some ({inner}) else none)"
        else:
            return f"({iterable}).filter (fun {target} => {cond}).flatMap (fun {target} => {inner})"

    def _build_function_or_theorem(self, node, doc, stmts, args, is_thm, meta):
        """関数または定理のLean定義文字列を組み立てる"""
        body_lines = [self._v(s) for s in stmts] or ["sorry"]
        doc_prefix = f"/-- {doc} -/\n" if doc else ""
        
        if is_thm:
            # 定理の場合は最後のReturnを命題として抽出
            is_ret = isinstance(stmts[-1], ast.Return)
            prop = self._v(stmts[-1].value) if is_ret else "True"
            if is_ret: body_lines = body_lines[:-1]
            res = f"{doc_prefix}theorem {node.name} {args} : {prop} :=\n  " + "\n  ".join(body_lines + ["by sorry"])
        else:
            ret_type = types.translate_type(node.returns)
            res = f"{doc_prefix}def {node.name} {args} : {ret_type} :=\n  " + "\n  ".join(body_lines)

        is_rec, hint = meta.get("is_recursive", False), meta.get("hint")
        if is_rec:
            res += f"\ntermination_by {hint}" if hint else ""
            if not hint:
                res = f"-- [PyLean] Warning: No termination measure found.\n{res}"
        return res

# --- ビルトイン関数・メソッド変換用レジストリ ---

def _handle_decimal_call(node, visitor):
    if len(node.args) == 1 and isinstance(node.args[0], ast.Constant):
        try:
            f = fractions.Fraction(node.args[0].value)
            return f"({f.numerator}/{f.denominator} : Rat)"
        except Exception: pass
    return None

def _handle_unary_call(lean_func):
    return lambda node, visitor: f"({lean_func} {visitor._v(node.args[0])})" if len(node.args) == 1 else None

def _handle_min_max_call(node, visitor):
    func_name = visitor._v(node.func)
    if len(node.args) >= 2:
        args_str = [visitor._v(arg) for arg in node.args]
        result = args_str[-1]
        for arg in reversed(args_str[:-1]):
            result = f"({func_name} {arg} {result})"
        return result
    return None

def _handle_date_call(node, visitor):
    if len(node.args) == 3:
        a = [visitor._v(arg) for arg in node.args]
        return f"({{ year := {a[0]}, month := {a[1]}, day := {a[2]} }} : Date)"
    return None

def _handle_quantize_method(node, visitor):
    target = visitor._v(node.func.value)
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