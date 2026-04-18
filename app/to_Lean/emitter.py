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