import ast
import os
import sys
import unittest

# プロジェクトルートを sys.path に追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.to_Lean.translator.context import TranslationContext
from app.to_Lean.translator.core import LeanTranslator
from app.to_Lean.translator.handlers.expressions import (
    OP_PRECEDENCE,
    _format_binop_operand,
    _should_wrap_operand,
    handle_binop,
    handle_boolop,
    handle_compare,
    handle_list_comp,
    handle_unaryop,
)


class TestExpressionsBase(unittest.TestCase):
    """AST パースおよび Translator 生成の基底ヘルパークラス"""

    def setUp(self):
        self.context = TranslationContext()
        self.visitor = LeanTranslator(self.context)

    def parse_expr(self, code_str: str) -> ast.AST:
        """式文字列をパースして式ノード (ast.AST) を返す"""
        parsed = ast.parse(code_str)
        expr = parsed.body[0]
        assert isinstance(expr, ast.Expr)
        return expr.value

    def translate_expr(self, code_str: str) -> str:
        """式文字列をパースして Visitor (LeanTranslator) で変換した結果を返す"""
        node = self.parse_expr(code_str)
        return self.visitor.visit(node)


class TestHelperFunctions(TestExpressionsBase):
    """_should_wrap_operand, _format_binop_operand などのヘルパー関数テスト"""

    def test_op_precedence_values(self):
        """演算子の優先順位テーブルの定義内容を確認"""
        self.assertEqual(OP_PRECEDENCE[ast.Pow], 30)
        self.assertEqual(OP_PRECEDENCE[ast.Mult], 20)
        self.assertEqual(OP_PRECEDENCE[ast.Div], 20)
        self.assertEqual(OP_PRECEDENCE[ast.FloorDiv], 20)
        self.assertEqual(OP_PRECEDENCE[ast.Mod], 20)
        self.assertEqual(OP_PRECEDENCE[ast.Add], 10)
        self.assertEqual(OP_PRECEDENCE[ast.Sub], 10)

    def test_should_wrap_operand_non_binop_compound(self):
        """IfExp, BoolOp, Compare は常にラップが必要と判定される"""
        if_exp = self.parse_expr("1 if cond else 0")
        bool_op = self.parse_expr("a and b")
        compare = self.parse_expr("a < b")

        self.assertTrue(_should_wrap_operand(ast.Add(), if_exp))
        self.assertTrue(_should_wrap_operand(ast.Mult(), bool_op))
        self.assertTrue(_should_wrap_operand(ast.Sub(), compare))

    def test_should_wrap_operand_atomic(self):
        """変数名や定数、関数呼び出しなどはラップ不要と判定される"""
        name_node = self.parse_expr("x")
        const_node = self.parse_expr("42")
        call_node = self.parse_expr("f(x)")

        self.assertFalse(_should_wrap_operand(ast.Add(), name_node))
        self.assertFalse(_should_wrap_operand(ast.Mult(), const_node))
        self.assertFalse(_should_wrap_operand(ast.Pow(), call_node))

    def test_should_wrap_operand_precedence(self):
        """子の優先度が親より低い場合はラップが必要、高い場合は不要"""
        add_node = self.parse_expr("a + b")
        mult_node = self.parse_expr("a * b")

        # (a + b) * c -> Mult 親の中の Add 子: ラップ必要
        self.assertTrue(_should_wrap_operand(ast.Mult(), add_node))
        # (a * b) + c -> Add 親の中の Mult 子: ラップ不要
        self.assertFalse(_should_wrap_operand(ast.Add(), mult_node))

    def test_should_wrap_operand_pow_associativity(self):
        """累乗 (Pow) は右結合のため、左オペランドに同一優先度の Pow が来たらラップ必要"""
        pow_node = self.parse_expr("a ** b")
        # (a ** b) ** c: 左側はラップ必要
        self.assertTrue(_should_wrap_operand(ast.Pow(), pow_node, is_right=False))
        # a ** (b ** c): 右側はラップ不要
        self.assertFalse(_should_wrap_operand(ast.Pow(), pow_node, is_right=True))

    def test_should_wrap_operand_left_associative_right_operand(self):
        """左結合の減算・除算・剰余等の右オペランドに同等優先度が来る場合はラップ必要"""
        sub_node = self.parse_expr("b - c")
        add_node = self.parse_expr("b + c")
        mult_node = self.parse_expr("b * c")
        div_node = self.parse_expr("b / c")

        # a - (b - c)
        self.assertTrue(_should_wrap_operand(ast.Sub(), sub_node, is_right=True))
        # a - (b + c)
        self.assertTrue(_should_wrap_operand(ast.Sub(), add_node, is_right=True))
        # (a - b) - c : 左オペランドはラップ不要
        self.assertFalse(_should_wrap_operand(ast.Sub(), sub_node, is_right=False))

        # a / (b * c)
        self.assertTrue(_should_wrap_operand(ast.Div(), mult_node, is_right=True))
        # a / (b / c)
        self.assertTrue(_should_wrap_operand(ast.Div(), div_node, is_right=True))
        # a // (b * c)
        self.assertTrue(_should_wrap_operand(ast.FloorDiv(), mult_node, is_right=True))
        # a % (b * c)
        self.assertTrue(_should_wrap_operand(ast.Mod(), mult_node, is_right=True))

    def test_format_binop_operand(self):
        """_format_binop_operand が判定に従って正しく括弧を付与するか"""
        add_node = self.parse_expr("a + b")
        name_node = self.parse_expr("c")

        # Mult のオペランドとしての (a + b) はラップされる
        formatted_wrap = _format_binop_operand(self.visitor, ast.Mult(), add_node)
        self.assertEqual(formatted_wrap, "(a + b)")

        # Mult のオペランドとしての c はラップされない
        formatted_nowrap = _format_binop_operand(self.visitor, ast.Mult(), name_node)
        self.assertEqual(formatted_nowrap, "c")


class TestHandleBinOp(TestExpressionsBase):
    """二項演算 (handle_binop) のテスト"""

    def test_basic_arithmetic_operations(self):
        """基本的な算術演算子の変換"""
        self.assertEqual(self.translate_expr("a + b"), "a + b")
        self.assertEqual(self.translate_expr("a - b"), "a - b")
        self.assertEqual(self.translate_expr("a * b"), "a * b")
        self.assertEqual(self.translate_expr("a // b"), "a / b")
        self.assertEqual(self.translate_expr("a % b"), "a % b")
        self.assertEqual(self.translate_expr("a ** b"), "a ^ b")

    def test_division_operation(self):
        """除算 (py_div) の変換と引数ラッピング"""
        self.assertEqual(self.translate_expr("a / b"), "py_div a b")
        self.assertEqual(self.translate_expr("(a + b) / (c * d)"), "py_div (a + b) (c * d)")
        self.assertEqual(self.translate_expr("f(x) / g(y)"), "py_div (f x) (g y)")
        self.assertEqual(self.translate_expr("(1 if c else 0) / 2"), "py_div (if c then 1 else 0) 2")
        self.assertEqual(self.translate_expr("(a and b) / 2"), "py_div ((a && b)) 2")
        self.assertEqual(self.translate_expr("(a < b) / 2"), "py_div ((a < b)) 2")

    def test_float_to_rat_cast_left(self):
        """左オペランドが浮動小数点数定数の場合の Rat キャスト"""
        self.assertEqual(self.translate_expr("0.5 + x"), "(1/2 : Rat) + (x : Rat)")
        self.assertEqual(self.translate_expr("0.5 * (a + b)"), "(1/2 : Rat) * ((a + b) : Rat)")

    def test_float_to_rat_cast_right(self):
        """右オペランドが浮動小数点数定数の場合の Rat キャスト"""
        self.assertEqual(self.translate_expr("x + 0.5"), "(x : Rat) + (1/2 : Rat)")
        self.assertEqual(self.translate_expr("(a + b) * 0.5"), "((a + b) : Rat) * (1/2 : Rat)")

    def test_float_to_rat_cast_both(self):
        """両オペランドが浮動小数点数定数の場合は既存の Rat 表現がそのまま使われる"""
        self.assertEqual(self.translate_expr("0.5 + 1.5"), "(1/2 : Rat) + (3/2 : Rat)")

    def test_float_to_rat_cast_division(self):
        """除算と float 定数の組み合わせ"""
        self.assertEqual(self.translate_expr("x / 0.5"), "py_div (x : Rat) (1/2 : Rat)")
        self.assertEqual(self.translate_expr("0.5 / x"), "py_div (1/2 : Rat) (x : Rat)")

    def test_operator_precedence_and_grouping(self):
        """演算子の優先順位に応じた括弧付け"""
        self.assertEqual(self.translate_expr("(a + b) * c"), "(a + b) * c")
        self.assertEqual(self.translate_expr("a + b * c"), "a + b * c")
        self.assertEqual(self.translate_expr("a * (b + c)"), "a * (b + c)")
        self.assertEqual(self.translate_expr("(a * b) ** c"), "(a * b) ^ c")
        self.assertEqual(self.translate_expr("a ** (b * c)"), "a ^ (b * c)")

    def test_associativity_grouping(self):
        """結合性に応じた括弧付け (累乗, 減算, 剰余など)"""
        # 累乗 (右結合)
        self.assertEqual(self.translate_expr("(a ** b) ** c"), "(a ^ b) ^ c")
        self.assertEqual(self.translate_expr("a ** (b ** c)"), "a ^ b ^ c")
        # 減算 (左結合)
        self.assertEqual(self.translate_expr("a - (b - c)"), "a - (b - c)")
        self.assertEqual(self.translate_expr("(a - b) - c"), "a - b - c")
        # 除算 (左結合)
        self.assertEqual(self.translate_expr("a // (b // c)"), "a / (b / c)")
        # 剰余 (左結合)
        self.assertEqual(self.translate_expr("a % (b % c)"), "a % (b % c)")

    def test_binop_with_other_expressions(self):
        """三項演算子、論理演算、比較演算が二項演算のオペランドにある場合"""
        self.assertEqual(self.translate_expr("(1 if cond else 0) + 2"), "(if cond then 1 else 0) + 2")
        self.assertEqual(self.translate_expr("(a and b) + c"), "((a && b)) + c")
        self.assertEqual(self.translate_expr("(a == b) + c"), "((a == b)) + c")

    def test_unsupported_binop(self):
        """未対応の二項演算子 (BitAnd, BitOr, BitXor など)"""
        self.assertIn("-- [Unsupported] BinOp:", self.translate_expr("a & b"))
        self.assertIn("-- [Unsupported] BinOp:", self.translate_expr("a | b"))
        self.assertIn("-- [Unsupported] BinOp:", self.translate_expr("a ^ b"))


class TestHandleUnaryOp(TestExpressionsBase):
    """単項演算 (handle_unaryop) のテスト"""

    def test_unary_sub(self):
        """単項マイナス"""
        self.assertEqual(self.translate_expr("-x"), "(-x)")

    def test_unary_add(self):
        """単項プラス"""
        self.assertEqual(self.translate_expr("+x"), "(+x)")

    def test_unary_not(self):
        """論理否定 not"""
        self.assertEqual(self.translate_expr("not x"), "(!x)")

    def test_unary_nested_expressions(self):
        """複合式に対する単項演算"""
        self.assertEqual(self.translate_expr("-(a + b)"), "(-(a + b))")
        self.assertEqual(self.translate_expr("not (a and b)"), "(!((a && b)))")
        self.assertEqual(self.translate_expr("not (x > 0)"), "(!((x > 0)))")

    def test_unsupported_unaryop(self):
        """未対応の単項演算子 (Invert ~ など)"""
        self.assertIn("-- [Unsupported] UnaryOp:", self.translate_expr("~x"))


class TestHandleBoolOp(TestExpressionsBase):
    """論理演算 (handle_boolop) のテスト"""

    def test_boolop_and(self):
        """and 演算"""
        self.assertEqual(self.translate_expr("a and b"), "(a && b)")

    def test_boolop_or(self):
        """or 演算"""
        self.assertEqual(self.translate_expr("a or b"), "(a || b)")

    def test_boolop_multiple_operands(self):
        """3つ以上のオペランドの連鎖"""
        self.assertEqual(self.translate_expr("a and b and c"), "(a && b && c)")
        self.assertEqual(self.translate_expr("a or b or c"), "(a || b || c)")

    def test_boolop_nested(self):
        """and と or の組み合わせ・ネスト"""
        self.assertEqual(self.translate_expr("(a or b) and (c or d)"), "(((a || b)) && ((c || d)))")

    def test_boolop_with_comparisons(self):
        """比較式を含む論理演算"""
        self.assertEqual(self.translate_expr("x > 0 and y < 10"), "(((x > 0)) && ((y < 10)))")


class TestHandleCompare(TestExpressionsBase):
    """比較演算 (handle_compare) のテスト"""

    def test_basic_comparisons(self):
        """単一の比較演算"""
        self.assertEqual(self.translate_expr("a == b"), "(a == b)")
        self.assertEqual(self.translate_expr("a != b"), "(a != b)")
        self.assertEqual(self.translate_expr("a < b"), "(a < b)")
        self.assertEqual(self.translate_expr("a <= b"), "(a <= b)")
        self.assertEqual(self.translate_expr("a > b"), "(a > b)")
        self.assertEqual(self.translate_expr("a >= b"), "(a >= b)")

    def test_chained_comparisons(self):
        """連鎖比較演算 (a < b < c)"""
        self.assertEqual(self.translate_expr("0 <= x < 10"), "((0 <= x) && (x < 10))")
        self.assertEqual(
            self.translate_expr("a < b <= c == d"),
            "((a < b) && (b <= c) && (c == d))",
        )

    def test_unsupported_comparison_operators(self):
        """未対応の比較演算子 (in, not in, is, is not)"""
        self.assertEqual(self.translate_expr("a in b"), "(a ? b)")
        self.assertEqual(self.translate_expr("a not in b"), "(a ? b)")
        self.assertEqual(self.translate_expr("a is b"), "(a ? b)")
        self.assertEqual(self.translate_expr("a is not b"), "(a ? b)")


class TestHandleListComp(TestExpressionsBase):
    """リスト内包表記 (handle_list_comp) のテスト"""

    def test_simple_list_comp(self):
        """条件なしのシンプルな内包表記"""
        self.assertEqual(self.translate_expr("[x for x in xs]"), "(xs).map (fun x => x)")
        self.assertEqual(self.translate_expr("[x * 2 for x in xs]"), "(xs).map (fun x => x * 2)")

    def test_list_comp_with_single_condition(self):
        """単一の if 条件を持つ内包表記"""
        self.assertEqual(
            self.translate_expr("[x * 2 for x in xs if x > 0]"),
            "(xs).filterMap (fun x => if ((x > 0)) then some (x * 2) else none)",
        )

    def test_list_comp_with_multiple_conditions(self):
        """複数の if 条件を持つ内包表記"""
        self.assertEqual(
            self.translate_expr("[x * 2 for x in xs if x > 0 if x < 10]"),
            "(xs).filterMap (fun x => if ((x > 0)) && ((x < 10)) then some (x * 2) else none)",
        )

    def test_nested_list_comp_two_generators(self):
        """2重ループの内包表記 (flatMap + map)"""
        self.assertEqual(
            self.translate_expr("[x + y for x in xs for y in ys]"),
            "(xs).flatMap (fun x => (ys).map (fun y => x + y))",
        )

    def test_nested_list_comp_with_outer_condition(self):
        """外側ループに条件がある内包表記"""
        self.assertEqual(
            self.translate_expr("[x + y for x in xs if x > 0 for y in ys]"),
            "(xs).filter (fun x => ((x > 0))).flatMap (fun x => (ys).map (fun y => x + y))",
        )

    def test_nested_list_comp_with_inner_condition(self):
        """内側ループに条件がある内包表記"""
        self.assertEqual(
            self.translate_expr("[x + y for x in xs for y in ys if y > 0]"),
            "(xs).flatMap (fun x => (ys).filterMap (fun y => if ((y > 0)) then some (x + y) else none))",
        )

    def test_nested_list_comp_with_both_conditions(self):
        """外側・内側の両ループに条件がある内包表記"""
        self.assertEqual(
            self.translate_expr("[x + y for x in xs if x > 0 for y in ys if y > 0]"),
            "(xs).filter (fun x => ((x > 0))).flatMap (fun x => (ys).filterMap (fun y => if ((y > 0)) then some (x + y) else none))",
        )

    def test_nested_list_comp_three_generators(self):
        """3重ループの内包表記"""
        self.assertEqual(
            self.translate_expr("[x + y + z for x in xs for y in ys for z in zs]"),
            "(xs).flatMap (fun x => (ys).flatMap (fun y => (zs).map (fun z => x + y + z)))",
        )


class TestDirectHandlerInvocation(TestExpressionsBase):
    """各ハンドラ関数を直接呼び出した場合のテスト"""

    def test_direct_handle_binop(self):
        node = self.parse_expr("a + b")
        assert isinstance(node, ast.BinOp)
        self.assertEqual(handle_binop(node, self.visitor), "a + b")

    def test_direct_handle_unaryop(self):
        node = self.parse_expr("-x")
        assert isinstance(node, ast.UnaryOp)
        self.assertEqual(handle_unaryop(node, self.visitor), "(-x)")

    def test_direct_handle_boolop(self):
        node = self.parse_expr("a and b")
        assert isinstance(node, ast.BoolOp)
        self.assertEqual(handle_boolop(node, self.visitor), "(a && b)")

    def test_direct_handle_compare(self):
        node = self.parse_expr("a < b")
        assert isinstance(node, ast.Compare)
        self.assertEqual(handle_compare(node, self.visitor), "(a < b)")

    def test_direct_handle_list_comp(self):
        node = self.parse_expr("[x for x in xs]")
        assert isinstance(node, ast.ListComp)
        self.assertEqual(handle_list_comp(node, self.visitor), "(xs).map (fun x => x)")


if __name__ == "__main__":
    unittest.main()
