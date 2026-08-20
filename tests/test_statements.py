import ast
import os
import sys
import unittest
from unittest.mock import MagicMock

# プロジェクトルートを sys.path に追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.to_Lean.translator.context import TranslationContext
from app.to_Lean.translator.core import LeanTranslator
from app.to_Lean.translator.handlers.statements import (
    handle_aug_assign,
    handle_class_def,
    handle_function_def,
    handle_if,
)


class TestStatementsBase(unittest.TestCase):
    """AST パースおよび Translator 生成の基底ヘルパークラス"""

    def setUp(self):
        self.context = TranslationContext()
        self.visitor = LeanTranslator(self.context)

    def parse_stmt(self, code_str: str) -> ast.stmt:
        """ステートメント文字列をパースして先頭の ast.stmt を返す"""
        parsed = ast.parse(code_str)
        self.assertTrue(len(parsed.body) > 0)
        return parsed.body[0]

    def translate_stmt(self, code_str: str) -> str:
        """ステートメント文字列をパースして LeanTranslator で変換した結果を返す"""
        node = self.parse_stmt(code_str)
        return self.visitor.visit(node)


class TestHandleAugAssign(TestStatementsBase):
    """累積代入 (handle_aug_assign) のテスト"""

    def test_aug_assign_add(self):
        """x += y -> let x := x + y;"""
        self.assertEqual(self.translate_stmt("x += y"), "let x := x + y;")

    def test_aug_assign_sub(self):
        """x -= 1 -> let x := x - 1;"""
        self.assertEqual(self.translate_stmt("x -= 1"), "let x := x - 1;")

    def test_aug_assign_mult(self):
        """total *= rate -> let total := total * rate;"""
        self.assertEqual(self.translate_stmt("total *= rate"), "let total := total * rate;")

    def test_aug_assign_div(self):
        """x /= 2 -> let x := x / 2;"""
        self.assertEqual(self.translate_stmt("x /= 2"), "let x := x / 2;")

    def test_aug_assign_floordiv(self):
        """x //= 2 -> let x := x / 2;"""
        self.assertEqual(self.translate_stmt("x //= 2"), "let x := x / 2;")

    def test_aug_assign_mod(self):
        """x %= 10 -> let x := x % 10;"""
        self.assertEqual(self.translate_stmt("x %= 10"), "let x := x % 10;")

    def test_aug_assign_pow(self):
        """x **= 2 -> let x := x ^ 2;"""
        self.assertEqual(self.translate_stmt("x **= 2"), "let x := x ^ 2;")

    def test_aug_assign_attribute_target(self):
        """obj.attr += 1 -> let obj.attr := obj.attr + 1;"""
        self.assertEqual(self.translate_stmt("obj.attr += 1"), "let obj.attr := obj.attr + 1;")

    def test_aug_assign_unsupported_op_fallback(self):
        """未定義の演算子の場合の '??' フォールバック"""
        node = self.parse_stmt("x &= 1")
        assert isinstance(node, ast.AugAssign)
        self.assertEqual(handle_aug_assign(node, self.visitor), "let x := x ?? 1;")


class TestHandleIf(TestStatementsBase):
    """If文 (handle_if) のテスト"""

    def test_if_without_else(self):
        """else 節のない if 文 (デフォルトで else 0 を補完)"""
        code = (
            "if x > 0:\n"
            "    return x"
        )
        expected = (
            "if (x > 0) then\n"
            "  x\n"
            "else\n"
            "  0"
        )
        self.assertEqual(self.translate_stmt(code), expected)

    def test_if_with_else(self):
        """else 節のある if-else 文"""
        code = (
            "if x > 0:\n"
            "    return x\n"
            "else:\n"
            "    return -x"
        )
        expected = (
            "if (x > 0) then\n"
            "  x\n"
            "else\n"
            "  (-x)"
        )
        self.assertEqual(self.translate_stmt(code), expected)

    def test_if_elif_else(self):
        """elif を含む if-elif-else 文"""
        code = (
            "if x > 0:\n"
            "    return 1\n"
            "elif x < 0:\n"
            "    return -1\n"
            "else:\n"
            "    return 0"
        )
        expected = (
            "if (x > 0) then\n"
            "  1\n"
            "else if (x < 0) then\n"
            "  (-1)\n"
            "else\n"
            "  0"
        )
        self.assertEqual(self.translate_stmt(code), expected)

    def test_if_multiple_elif(self):
        """複数段の elif を含む条件分岐"""
        code = (
            "if x == 1:\n"
            "    return 10\n"
            "elif x == 2:\n"
            "    return 20\n"
            "elif x == 3:\n"
            "    return 30\n"
            "else:\n"
            "    return 0"
        )
        expected = (
            "if (x == 1) then\n"
            "  10\n"
            "else if (x == 2) then\n"
            "  20\n"
            "else if (x == 3) then\n"
            "  30\n"
            "else\n"
            "  0"
        )
        self.assertEqual(self.translate_stmt(code), expected)

    def test_if_multiple_body_statements(self):
        """then 節に複数行のステートメントがある場合"""
        code = (
            "if cond:\n"
            "    a = 1\n"
            "    return a\n"
            "else:\n"
            "    return 0"
        )
        expected = (
            "if cond then\n"
            "  let a := 1;\n"
            "  a\n"
            "else\n"
            "  0"
        )
        self.assertEqual(self.translate_stmt(code), expected)

    def test_if_multiple_else_statements(self):
        """else 節に複数行のステートメントがある場合"""
        code = (
            "if cond:\n"
            "    return 1\n"
            "else:\n"
            "    b = 2\n"
            "    return b"
        )
        expected = (
            "if cond then\n"
            "  1\n"
            "else\n"
            "  let b := 2;\n"
            "  b"
        )
        self.assertEqual(self.translate_stmt(code), expected)


class TestHandleFunctionDef(TestStatementsBase):
    """関数定義および定理定義 (handle_function_def) のテスト"""

    def test_simple_function_def(self):
        """通常の関数定義 (def)"""
        code = (
            "def add(a: int, b: int) -> int:\n"
            "    return a + b"
        )
        expected = "def add (a : Int) (b : Int) : Int :=\n  a + b"
        self.assertEqual(self.translate_stmt(code), expected)

    def test_function_def_with_docstring(self):
        """Docstring を持つ関数定義"""
        code = (
            "def add(a: int, b: int) -> int:\n"
            "    \"\"\"Add two integers.\"\"\"\n"
            "    return a + b"
        )
        expected = "/-- Add two integers. -/\ndef add (a : Int) (b : Int) : Int :=\n  a + b"
        self.assertEqual(self.translate_stmt(code), expected)

    def test_function_def_with_preconditions(self):
        """事前条件 (preconditions) を持つ関数定義"""
        code = (
            "def calc(a: int) -> int:\n"
            "    assert a > 0\n"
            "    return a * 2"
        )
        parsed = ast.parse(code).body[0]
        # 解析フェーズと同じ AST ノードインスタンスを事前条件として登録
        self.context.functions["calc"] = {"preconditions": [parsed.body[0].test]}

        expected = "def calc (a : Int) (h_precond_0 : (a > 0)) : Int :=\n  a * 2"
        self.assertEqual(self.visitor.visit(parsed), expected)

    def test_theorem_def_verify_prefix(self):
        """verify_ プレフィックスの定理定義 (theorem)"""
        code = (
            "def verify_addition(a: int, b: int) -> bool:\n"
            "    return add(a, b) == a + b"
        )
        expected = "theorem verify_addition (a : Int) (b : Int) : (add a b == a + b) :=\n  rfl"
        self.assertEqual(self.translate_stmt(code), expected)

    def test_theorem_def_theorem_prefix(self):
        """theorem_ プレフィックスの定理定義 (theorem)"""
        code = (
            "def theorem_addition(a: int, b: int) -> bool:\n"
            "    return add(a, b) == a + b"
        )
        expected = "theorem theorem_addition (a : Int) (b : Int) : (add a b == a + b) :=\n  rfl"
        self.assertEqual(self.translate_stmt(code), expected)

    def test_theorem_def_with_statements(self):
        """複数ステートメント（assert 等）を含む定理定義"""
        code = (
            "def verify_calc(x: int) -> bool:\n"
            "    assert x > 0\n"
            "    return x + 1 > 1"
        )
        expected = (
            "theorem verify_calc (x : Int) : (x + 1 > 1) :=\n"
            "  have h_assert_0 : (x > 0) := by sorry\n"
            "  by sorry"
        )
        self.assertEqual(self.translate_stmt(code), expected)

    def test_theorem_def_inherits_target_preconditions(self):
        """定理が被検証関数 (target) の事前条件を引き継ぐ"""
        cond_node = ast.parse("x > 0").body[0].value
        self.context.functions["target_fn"] = {"preconditions": [cond_node]}

        code = (
            "def verify_target_fn(x: int) -> bool:\n"
            "    return target_fn(x) > 0"
        )
        expected = "theorem verify_target_fn (x : Int) (h_precond_0 : (x > 0)) : (target_fn x h_precond_0 > 0) :=\n  rfl"
        self.assertEqual(self.translate_stmt(code), expected)

    def test_recursive_function_with_termination_hint(self):
        """停止性ヒント (hint) を持つ再帰関数"""
        self.context.functions["count_down"] = {
            "is_recursive": True,
            "hint": "n",
        }
        code = (
            "def count_down(n: int) -> int:\n"
            "    return count_down(n - 1) if n > 0 else 0"
        )
        res = self.translate_stmt(code)
        self.assertIn("termination_by n", res)
        self.assertNotIn("Warning: No termination measure found", res)

    def test_recursive_function_without_termination_hint_warning(self):
        """停止性ヒントを持たない再帰関数の警告出力"""
        self.context.functions["infinite_loop"] = {
            "is_recursive": True,
        }
        code = (
            "def infinite_loop(n: int) -> int:\n"
            "    return infinite_loop(n)"
        )
        res = self.translate_stmt(code)
        self.assertIn("-- [PyLean] Warning: No termination measure found.", res)


class TestHandleClassDef(TestStatementsBase):
    """クラス定義 (handle_class_def) のテスト"""

    def test_class_def_enum(self):
        """Enum クラス定義 (inductive に変換)"""
        self.context.classes["Color"] = "enum"
        code = (
            "class Color:\n"
            "    RED = 1\n"
            "    GREEN = 2\n"
            "    BLUE = 3"
        )
        expected = (
            "inductive Color where\n"
            "  | RED\n"
            "  | GREEN\n"
            "  | BLUE\n"
            "  deriving Repr, BEq"
        )
        self.assertEqual(self.translate_stmt(code), expected)

    def test_class_def_dataclass_structure(self):
        """Dataclass / Structure クラス定義 (structure に変換)"""
        self.context.classes["Point"] = "structure"
        code = (
            "class Point:\n"
            "    x: float\n"
            "    y: float\n"
            "    name: str"
        )
        expected = (
            "structure Point where\n"
            "  x : Rat\n"
            "  y : Rat\n"
            "  name : String\n"
            "  deriving Repr, BEq"
        )
        self.assertEqual(self.translate_stmt(code), expected)

    def test_class_def_unsupported(self):
        """Enum でも Dataclass でもない通常のクラス (未対応メッセージ)"""
        code = (
            "class RegularClass:\n"
            "    pass"
        )
        result = self.translate_stmt(code)
        self.assertIn("-- [Unsupported] ClassDef: Only Enums and @dataclass are supported", result)


class TestDirectHandlerInvocation(TestStatementsBase):
    """各ハンドラ関数を直接呼び出すテスト"""

    def test_direct_handle_aug_assign(self):
        node = self.parse_stmt("x += 5")
        assert isinstance(node, ast.AugAssign)
        self.assertEqual(handle_aug_assign(node, self.visitor), "let x := x + 5;")

    def test_direct_handle_if(self):
        node = self.parse_stmt("if c:\n    return 1\nelse:\n    return 2")
        assert isinstance(node, ast.If)
        res = handle_if(node, self.visitor)
        self.assertIn("if c then", res)

    def test_direct_handle_function_def(self):
        node = self.parse_stmt("def f(x: int) -> int:\n    return x")
        assert isinstance(node, ast.FunctionDef)
        res = handle_function_def(node, self.visitor)
        self.assertIn("def f (x : Int) : Int :=", res)

    def test_direct_handle_class_def(self):
        self.context.classes["Status"] = "enum"
        node = self.parse_stmt("class Status:\n    OK = 1\n    NG = 2")
        assert isinstance(node, ast.ClassDef)
        res = handle_class_def(node, self.visitor)
        self.assertIn("inductive Status where", res)


class TestStatementsWithMockVisitor(unittest.TestCase):
    """モック Visitor を用いた独立したハンドラ単体テスト"""

    def setUp(self):
        self.mock_v = MagicMock()
        def mock_v_func(node):
            if isinstance(node, ast.Name):
                return node.id
            if isinstance(node, ast.Constant):
                return str(node.value)
            if isinstance(node, ast.Return):
                return mock_v_func(node.value)
            if isinstance(node, ast.If):
                return "if_inner_res"
            return "dummy"
        self.mock_v._v.side_effect = mock_v_func
        self.mock_v.context = MagicMock()
        self.mock_v.context.classes = {}
        self.mock_v.context.functions = {}

    def test_mock_handle_aug_assign(self):
        node = ast.AugAssign(
            target=ast.Name(id="count", ctx=ast.Store()),
            op=ast.Add(),
            value=ast.Constant(value=1),
        )
        result = handle_aug_assign(node, self.mock_v)
        self.assertEqual(result, "let count := count + 1;")

    def test_mock_handle_if_elif(self):
        inner_if = ast.If(
            test=ast.Name(id="c2", ctx=ast.Load()),
            body=[ast.Return(value=ast.Constant(value=2))],
            orelse=[ast.Return(value=ast.Constant(value=3))],
        )
        outer_if = ast.If(
            test=ast.Name(id="c1", ctx=ast.Load()),
            body=[ast.Return(value=ast.Constant(value=1))],
            orelse=[inner_if],
        )
        handle_if(outer_if, self.mock_v)
        self.mock_v.emitter.format_if_stmt.assert_called_with(
            "c1", ["1"], ["if_inner_res"], is_elif=True
        )

    def test_mock_handle_class_def_unsupported(self):
        node = ast.ClassDef(name="UnknownClass", bases=[], keywords=[], body=[], decorator_list=[])
        self.mock_v.context.classes = {}
        self.mock_v._unsupported.return_value = "-- [Unsupported] ClassDef: Only Enums and @dataclass are supported"
        result = handle_class_def(node, self.mock_v)
        self.mock_v._unsupported.assert_called_with(node, "Only Enums and @dataclass are supported")
        self.assertEqual(result, "-- [Unsupported] ClassDef: Only Enums and @dataclass are supported")


if __name__ == "__main__":
    unittest.main()

