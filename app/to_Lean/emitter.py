from __future__ import annotations

from fractions import Fraction
from typing import TYPE_CHECKING, Any, Iterable, Sequence

from .translator import constants

if TYPE_CHECKING:
    from .translator.context import TranslationContext


class LeanEmitter:
    """Lean 4 のコード文字列を生成するためのフォーマッタクラス"""

    def __init__(self, context: TranslationContext) -> None:
        self.context: TranslationContext = context

    def _format_doc(self, doc: str | None) -> str:
        """DocstringをLeanのコメント形式に変換する"""
        if not doc:
            return ""
        return constants.DOC_TEMPLATE.format(doc=doc) + "\n"

    def format_constant(self, value: Any) -> str:
        """定数を整形する"""
        return f'"{value}"' if isinstance(value, str) else str(value)

    def format_rat_constant(self, value: float | int) -> str:
        """浮動小数点数を有理数 (Rat) 形式に整形する"""
        f = Fraction(value).limit_denominator()
        return f"({f.numerator}/{f.denominator} : Rat)"

    def format_attribute(self, value: str, attr: str) -> str:
        """属性アクセス (obj.attr) を整形する"""
        return f"{value}.{attr}"

    def format_assign(self, target: str, value: str) -> str:
        """変数代入 (let) を整形する"""
        return f"let {target} := {value};"

    def format_assert(self, test: str, label: str | None = None) -> str:
        """アサーションを整形する"""
        if label:
            return f"have {label} : {test} := by sorry"
        return f"have : {test} := by sorry"

    def format_if_exp(self, test: str, body: str, orelse: str) -> str:
        """三項演算子 (IfExp) を整形する"""
        return f"if {test} then {body} else {orelse}"

    def format_collection(
        self,
        elements: Sequence[str] | Iterable[str],
        prefix: str = "[",
        suffix: str = "]",
    ) -> str:
        """リストやタプルを整形する"""
        return f"{prefix}{', '.join(elements)}{suffix}"

    def format_binop(
        self,
        left: str,
        op_str: str,
        right: str,
        is_div: bool = False,
    ) -> str:
        """二項演算を整形する"""
        if is_div:
            return f"py_div {left} {right}"
        return f"{left} {op_str} {right}"

    def format_unaryop(self, op_str: str, operand: str) -> str:
        """単項演算を整形する"""
        return f"({op_str}{operand})"

    def format_boolop(
        self,
        op_str: str,
        values: Sequence[str] | Iterable[str],
    ) -> str:
        """論理演算 (and, or) を整形する"""
        return f"({(f' {op_str} ').join(values)})"

    def format_compare(self, parts: Sequence[str]) -> str:
        """比較演算の連鎖を整形する"""
        return parts[0] if len(parts) == 1 else f"({' && '.join(parts)})"

    def format_if_stmt(
        self,
        test: str,
        then_lines: Sequence[str],
        else_lines: Sequence[str],
        is_elif: bool = False,
    ) -> str:
        """If-Else 文を整形する"""
        then_part = "\n  ".join(then_lines)
        res = f"if {test} then\n  {then_part}"
        if else_lines:
            if is_elif:
                # else if の場合、インデントを下げずに else に続けて if ... を出力
                res += f"\nelse {else_lines[0]}"
            else:
                else_part = "\n  ".join(else_lines)
                res += f"\nelse\n  {else_part}"
        return res

    def format_example(self, prop: str, proof: str = "rfl") -> str:
        """example (値のテスト) を整形する"""
        return f"example : {prop} := {proof}"

    def format_theorem(
        self,
        name: str,
        args: str,
        prop: str,
        body_lines: Sequence[str],
        doc: str | None = None,
    ) -> str:
        """定理 (theorem) を整形する"""
        doc_str = self._format_doc(doc)
        body = "\n  ".join(body_lines)
        if body.strip() == "rfl":
            return f"{doc_str}theorem {name} {args} : {prop} :=\n  rfl"
        return f"{doc_str}theorem {name} {args} : {prop} :=\n  {body}\n  by sorry"

    def format_function(
        self,
        name: str,
        args: str,
        ret_type: str,
        body_lines: Sequence[str],
        doc: str | None = None,
        termination_hint: str | None = None,
        is_recursive: bool = False,
    ) -> str:
        """関数 (def) を整形する"""
        doc_str = self._format_doc(doc)
        body = "\n  ".join(body_lines)
        term = f"\ntermination_by {termination_hint}" if termination_hint else ""
        header = f"{doc_str}def {name} {args} : {ret_type} :="
        code = f"{header}\n  {body}{term}"

        if is_recursive and not termination_hint:
            return f"-- [PyLean] Warning: No termination measure found.\n{code}"
        return code

    def format_inductive(self, name: str, variants: Sequence[str]) -> str:
        """列挙型 (inductive) を整形する"""
        items = "\n  ".join([f"| {v}" for v in variants])
        return f"inductive {name} where\n  {items}\n  deriving Repr, BEq"

    def format_structure(
        self,
        name: str,
        fields: Sequence[tuple[str, str]],
    ) -> str:
        """構造体 (structure) を整形する"""
        items = "\n  ".join([f"{n} : {t}" for n, t in fields])
        return f"structure {name} where\n  {items}\n  deriving Repr, BEq"

    def format_list_comp_step(
        self,
        iterable: str,
        target: str,
        expr: str,
        cond_str: str | None = None,
        is_innermost: bool = False,
    ) -> str:
        """リスト内包表記の1ステップ（ジェネレータ）を整形する"""
        if is_innermost:
            if cond_str:
                return f"({iterable}).filterMap (fun {target} => if {cond_str} then some ({expr}) else none)"
            return f"({iterable}).map (fun {target} => {expr})"
        else:
            if cond_str:
                return f"({iterable}).filter (fun {target} => {cond_str}).flatMap (fun {target} => {expr})"
            return f"({iterable}).flatMap (fun {target} => {expr})"