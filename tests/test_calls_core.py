import ast
import os
import sys
import unittest

# プロジェクトルートを sys.path に追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.to_Lean.translator.context import TranslationContext
from app.to_Lean.translator.core import LeanTranslator
from app.to_Lean.translator.handlers.calls.core import (
    handle_call,
    BUILTIN_CALL_HANDLERS,
    METHOD_CALL_HANDLERS,
)


class TestCallsCoreBase(unittest.TestCase):
    """AST パースおよび Translator 生成の基底ヘルパークラス"""

    def setUp(self):
        self.context = TranslationContext()
        self.visitor = LeanTranslator(self.context)

    def parse_call(self, code_str: str) -> ast.Call:
        """式文字列をパースして ast.Call ノードを返す"""
        parsed = ast.parse(code_str)
        expr = parsed.body[0]
        assert isinstance(expr, ast.Expr) and isinstance(expr.value, ast.Call)
        return expr.value

    def translate_call(self, code_str: str) -> str:
        """式文字列から ast.Call を生成し、handle_call の結果文字列を返す"""
        node = self.parse_call(code_str)
        return handle_call(node, self.visitor)


class TestBuiltinCallHandlers(TestCallsCoreBase):
    """組み込み関数ハンドラ (math, accounting, datetime) のテスト"""

    def test_math_ceil(self):
        self.assertEqual(self.translate_call("ceil(x)"), "(py_ceil x)")
        self.assertEqual(self.translate_call("math.ceil(x)"), "(py_ceil x)")

    def test_math_floor(self):
        self.assertEqual(self.translate_call("floor(x)"), "(py_floor x)")
        self.assertEqual(self.translate_call("math.floor(x)"), "(py_floor x)")

    def test_math_round(self):
        self.assertEqual(self.translate_call("round(x)"), "(py_round x)")

    def test_math_sum(self):
        self.assertEqual(self.translate_call("sum(xs)"), "(py_sum xs)")

    def test_math_len(self):
        self.assertEqual(self.translate_call("len(xs)"), "(List.length xs)")

    def test_math_min_two_args(self):
        self.assertEqual(self.translate_call("min(a, b)"), "(min a b)")

    def test_math_min_multiple_args(self):
        self.assertEqual(self.translate_call("min(a, b, c)"), "(min a (min b c))")

    def test_math_max_multiple_args(self):
        self.assertEqual(self.translate_call("max(a, b, c, d)"), "(max a (max b (max c d)))")

    def test_decimal_string_literal(self):
        self.assertEqual(self.translate_call("Decimal('0.1')"), "(1/10 : Rat)")
        self.assertEqual(self.translate_call("Decimal('1.5')"), "(3/2 : Rat)")
        self.assertEqual(self.translate_call("decimal.Decimal('0.25')"), "(1/4 : Rat)")

    def test_decimal_fallback_non_literal(self):
        # 文字列リテラル以外の場合は組み込みハンドラが None を返し、通常の関数呼び出しにフォールスルーする
        self.assertEqual(self.translate_call("Decimal(x)"), "Decimal x")

    def test_date_constructor(self):
        self.assertEqual(
            self.translate_call("date(2025, 8, 15)"),
            "({ year := 2025, month := 8, day := 15 } : Date)",
        )
        self.assertEqual(
            self.translate_call("datetime.date(2025, 8, 15)"),
            "({ year := 2025, month := 8, day := 15 } : Date)",
        )

    def test_date_fallback_wrong_args(self):
        # 引数が3つ以外の場合は通常の関数呼び出しにフォールスルーする
        self.assertEqual(self.translate_call("date(2025, 8)"), "date 2025 8")


class TestMethodCallHandlers(TestCallsCoreBase):
    """メソッド呼び出しハンドラ (quantize など) のテスト"""

    def test_quantize_with_round_half_up(self):
        self.assertEqual(
            self.translate_call("x.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)"),
            "(py_round_half_up x)",
        )

    def test_unregistered_method_call(self):
        self.assertEqual(
            self.translate_call("obj.custom_method(arg1, arg2)"),
            "obj.custom_method arg1 arg2",
        )


class TestGenericFunctionCall(TestCallsCoreBase):
    """一般の関数呼び出しおよび引数ラッピング (_wrap) のテスト"""

    def test_call_no_arguments(self):
        self.assertEqual(self.translate_call("foo()"), "foo")

    def test_call_simple_arguments(self):
        self.assertEqual(self.translate_call("foo(a, b)"), "foo a b")

    def test_call_wrap_binary_operation(self):
        self.assertEqual(self.translate_call("foo(a + b, c * d)"), "foo (a + b) (c * d)")

    def test_call_wrap_nested_call(self):
        self.assertEqual(self.translate_call("foo(bar(x))"), "foo (bar x)")

    def test_call_wrap_if_expression(self):
        self.assertEqual(
            self.translate_call("calc(1 if cond else 0)"),
            "calc (if cond then 1 else 0)",
        )

    def test_call_wrap_comparison(self):
        self.assertEqual(self.translate_call("check(x > 0)"), "check ((x > 0))")

    def test_call_wrap_unary_operation(self):
        self.assertEqual(self.translate_call("neg(-x)"), "neg ((-x))")

    def test_call_wrap_bool_operation(self):
        self.assertEqual(self.translate_call("foo(a and b)"), "foo ((a && b))")


class TestPreconditionsHandling(TestCallsCoreBase):
    """事前条件 (Preconditions) 証明項の自動補完ロジックのテスト"""

    def _parse_expr(self, expr_str: str) -> ast.AST:
        return ast.parse(expr_str).body[0].value

    def test_precondition_matching(self):
        # 呼び出し先関数 'target_fn' に事前条件 [x > 0] を登録
        cond_x = self._parse_expr("x > 0")
        self.context.functions["target_fn"] = {"preconditions": [cond_x]}

        # 呼び出し元関数 'caller_fn' に事前条件 [x > 0] を登録
        self.context.functions["caller_fn"] = {"preconditions": [cond_x]}
        self.visitor.current_function = "caller_fn"

        result = self.translate_call("target_fn(x)")
        self.assertEqual(result, "target_fn x h_precond_0")

    def test_precondition_order_and_index(self):
        cond_x = self._parse_expr("x > 0")
        cond_y = self._parse_expr("y > 0")
        # 呼び出し先は [x > 0, y > 0]
        self.context.functions["target_fn"] = {"preconditions": [cond_x, cond_y]}

        # 呼び出し元は [y > 0, x > 0] (インデックスが 0: y > 0, 1: x > 0)
        self.context.functions["caller_fn"] = {"preconditions": [cond_y, cond_x]}
        self.visitor.current_function = "caller_fn"

        result = self.translate_call("target_fn(x, y)")
        self.assertEqual(result, "target_fn x y h_precond_1 h_precond_0")

    def test_precondition_not_matching_fallback_sorry(self):
        cond_target = self._parse_expr("x > 0")
        cond_caller = self._parse_expr("y > 0")
        self.context.functions["target_fn"] = {"preconditions": [cond_target]}
        self.context.functions["caller_fn"] = {"preconditions": [cond_caller]}
        self.visitor.current_function = "caller_fn"

        result = self.translate_call("target_fn(x)")
        self.assertEqual(result, "target_fn x (by sorry)")

    def test_precondition_verify_prefix_resolution(self):
        cond_x = self._parse_expr("x > 0")
        # 被検証関数 'calc' に事前条件を登録
        self.context.functions["calc"] = {"preconditions": [cond_x]}
        self.context.functions["helper"] = {"preconditions": [cond_x]}

        # 呼び出し元が 'verify_calc'
        self.visitor.current_function = "verify_calc"

        result = self.translate_call("helper(x)")
        self.assertEqual(result, "helper x h_precond_0")

    def test_precondition_theorem_prefix_resolution(self):
        cond_x = self._parse_expr("x > 0")
        self.context.functions["calc"] = {"preconditions": [cond_x]}
        self.context.functions["helper"] = {"preconditions": [cond_x]}

        # 呼び出し元が 'theorem_calc'
        self.visitor.current_function = "theorem_calc"

        result = self.translate_call("helper(x)")
        self.assertEqual(result, "helper x h_precond_0")

    def test_precondition_no_current_function(self):
        cond_x = self._parse_expr("x > 0")
        self.context.functions["target_fn"] = {"preconditions": [cond_x]}
        self.visitor.current_function = None

        result = self.translate_call("target_fn(x)")
        self.assertEqual(result, "target_fn x (by sorry)")


class TestHandlerConstants(unittest.TestCase):
    """テーブル定数の定義内容のテスト"""

    def test_builtin_handlers_contains_keys(self):
        expected_keys = {"ceil", "math.ceil", "Decimal", "date", "min", "max", "len", "sum"}
        for k in expected_keys:
            self.assertIn(k, BUILTIN_CALL_HANDLERS)

    def test_method_handlers_contains_keys(self):
        self.assertIn("quantize", METHOD_CALL_HANDLERS)


if __name__ == "__main__":
    unittest.main()
