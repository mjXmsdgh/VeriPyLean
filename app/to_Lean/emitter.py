from .translator import constants

class LeanEmitter:
    """Lean 4 のコード文字列を生成するためのフォーマッタクラス"""
    def __init__(self, context):
        self.context = context

    def _format_doc(self, doc):
        """DocstringをLeanのコメント形式に変換する"""
        if not doc:
            return ""
        return constants.DOC_TEMPLATE.format(doc=doc) + "\n"

    def format_constant(self, value):
        """定数を整形する"""
        return f'"{value}"' if isinstance(value, str) else str(value)

    def format_attribute(self, value, attr):
        """属性アクセス (obj.attr) を整形する"""
        return f"{value}.{attr}"

    def format_assign(self, target, value):
        """変数代入 (let) を整形する"""
        return f"let {target} := {value};"

    def format_assert(self, test):
        """アサーションを整形する"""
        return f"have : {test} := by sorry"

    def format_if_exp(self, test, body, orelse):
        """三項演算子 (IfExp) を整形する"""
        return f"if {test} then {body} else {orelse}"

    def format_collection(self, elements, prefix="[", suffix="]"):
        """リストやタプルを整形する"""
        return f"{prefix}{', '.join(elements)}{suffix}"

    def format_binop(self, left, op_str, right, is_div=False):
        """二項演算を整形する"""
        if is_div:
            return f"py_div {left} {right}"
        return f"{left} {op_str} {right}"

    def format_unaryop(self, op_str, operand):
        """単項演算を整形する"""
        return f"({op_str}{operand})"

    def format_boolop(self, op_str, values):
        """論理演算 (and, or) を整形する"""
        return f"({(f' {op_str} ').join(values)})"

    def format_compare(self, parts):
        """比較演算の連鎖を整形する"""
        return parts[0] if len(parts) == 1 else f"({' && '.join(parts)})"

    def format_if_stmt(self, test, then_lines, else_lines):
        """If-Else 文を整形する"""
        then_part = "\n  ".join(then_lines)
        res = f"if {test} then\n  {then_part}"
        if else_lines:
            else_part = "\n  ".join(else_lines)
            res += f"\nelse\n  {else_part}"
        return res

    def format_theorem(self, name, args, prop, body_lines, doc=None):
        """定理 (theorem) を整形する"""
        doc_str = self._format_doc(doc)
        body = "\n  ".join(body_lines)
        return f"{doc_str}theorem {name} {args} : {prop} :=\n  {body}\n  by sorry"

    def format_function(self, name, args, ret_type, body_lines, doc=None, termination_hint=None, is_recursive=False):
        """関数 (def) を整形する"""
        doc_str = self._format_doc(doc)
        body = "\n  ".join(body_lines)
        term = f"\ntermination_by {termination_hint}" if termination_hint else ""
        header = f"{doc_str}def {name} {args} : {ret_type} :="
        code = f"{header}\n  {body}{term}"
        
        if is_recursive and not termination_hint:
            return f"-- [PyLean] Warning: No termination measure found.\n{code}"
        return code

    def format_inductive(self, name, variants):
        """列挙型 (inductive) を整形する"""
        items = "\n  ".join([f"| {v}" for v in variants])
        return f"inductive {name} where\n  {items}\n  deriving Repr, BEq"

    def format_structure(self, name, fields):
        """構造体 (structure) を整形する"""
        items = "\n  ".join([f"{n} : {t}" for n, t in fields])
        return f"structure {name} where\n  {items}\n  deriving Repr, BEq"

    def format_list_comp_step(self, iterable, target, expr, cond_str=None, is_innermost=False):
        """リスト内包表記の1ステップ（ジェネレータ）を整形する"""
        if is_innermost:
            if cond_str:
                return f"({iterable}).filterMap (fun {target} => if {cond_str} then some ({expr}) else none)"
            return f"({iterable}).map (fun {target} => {expr})"
        else:
            if cond_str:
                return f"({iterable}).filter (fun {target} => {cond_str}).flatMap (fun {target} => {expr})"
            return f"({iterable}).flatMap (fun {target} => {expr})"