import ast
import os
import sys
import unittest
from unittest.mock import MagicMock

# プロジェクトルートを sys.path に追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.to_Lean.translator.context import TranslationContext
from app.to_Lean.translator.core import LeanTranslator, translate_to_lean


class TestTranslatorCoreBase(unittest.TestCase):
    """AST パースおよび Translator 生成の基底ヘルパークラス"""

    def setUp(self):
        self.context = TranslationContext()
        self.visitor = LeanTranslator(self.context)

    def parse_module(self, code_str: str) -> ast.Module:
        """コード文字列をパースして ast.Module を返す"""
        return ast.parse(code_str)

    def parse_stmt(self, code_str: str) -> ast.stmt:
        """ステートメント文字列をパースして先頭の ast.stmt を返す"""
        parsed = ast.parse(code_str)
        self.assertTrue(len(parsed.body) > 0)
        return parsed.body[0]

    def parse_expr(self, code_str: str) -> ast.AST:
        """式文字列をパースして式ノード (ast.AST) を返す"""
        parsed = ast.parse(code_str)
        expr = parsed.body[0]
        self.assertIsInstance(expr, ast.Expr)
        return expr.value

    def translate_code(self, code_str: str) -> str:
        """コード文字列をパースして LeanTranslator で変換した結果を返す"""
        node = self.parse_module(code_str)
        return self.visitor.visit(node)


class TestTranslateToLean(unittest.TestCase):
    """translate_to_lean エントリポイント関数のテスト"""

    def test_translate_to_lean_with_default_context(self):
        """context 省略時にデフォルトの TranslationContext が生成されて動作すること"""
        node = ast.parse("x = 10")
        result = translate_to_lean(node)
        self.assertEqual(result, "let x := 10;")

    def test_translate_to_lean_with_custom_context(self):
        """外部から渡された TranslationContext が使用されること"""
        custom_ctx = TranslationContext()
        custom_ctx.classes["Status"] = "enum"
        node = ast.parse("class Status:\n    OK = 1\n    NG = 2")
        result = translate_to_lean(node, context=custom_ctx)
        self.assertIn("inductive Status where", result)


class TestLeanTranslatorDispatch(TestTranslatorCoreBase):
    """基本ディスパッチテーブルおよび visit_Module のテスト"""

    def test_visit_module_multiple_statements(self):
        """複数ステートメントが改行2つで結合されること"""
        code = "a = 1\nb = 2\nc = 3"
        expected = "let a := 1;\n\nlet b := 2;\n\nlet c := 3;"
        self.assertEqual(self.translate_code(code), expected)

    def test_visit_module_empty(self):
        """空のモジュール"""
        self.assertEqual(self.translate_code(""), "")

    def test_dispatch_constants(self):
        """定数 (int, str, float) の変換"""
        # int
        self.assertEqual(self.visitor.visit(self.parse_expr("42")), "42")
        # str
        self.assertEqual(self.visitor.visit(self.parse_expr('"hello"')), '"hello"')
        # float -> Rat
        self.assertEqual(self.visitor.visit(self.parse_expr("0.5")), "(1/2 : Rat)")
        self.assertEqual(self.visitor.visit(self.parse_expr("1.25")), "(5/4 : Rat)")

    def test_dispatch_name_and_attribute(self):
        """変数名および属性アクセスの変換"""
        self.assertEqual(self.visitor.visit(self.parse_expr("variable")), "variable")
        self.assertEqual(self.visitor.visit(self.parse_expr("user.name")), "user.name")
        self.assertEqual(self.visitor.visit(self.parse_expr("a.b.c")), "a.b.c")

    def test_dispatch_pass(self):
        """pass 文 -> ()"""
        self.assertEqual(self.visitor.visit(self.parse_stmt("pass")), "()")

    def test_dispatch_assign_and_expr_and_return(self):
        """代入文、式文、return 文のディスパッチ"""
        self.assertEqual(self.visitor.visit(self.parse_stmt("x = 100")), "let x := 100;")
        self.assertEqual(self.visitor.visit(self.parse_stmt("f(x)")), "f x")
        self.assertEqual(self.visitor.visit(self.parse_stmt("return x + 1")), "x + 1")

    def test_dispatch_if_exp(self):
        """三項演算子 (IfExp)"""
        node = self.parse_expr("1 if cond else 2")
        self.assertEqual(self.visitor.visit(node), "if cond then 1 else 2")

    def test_dispatch_collections(self):
        """List および Tuple の変換"""
        self.assertEqual(self.visitor.visit(self.parse_expr("[1, 2, 3]")), "[1, 2, 3]")
        self.assertEqual(self.visitor.visit(self.parse_expr("(1, 2, 3)")), "(1, 2, 3)")

    def test_dispatch_fallback_super_visit(self):
        """ディスパッチテーブルにないノードに対する super().visit() フォールスルー"""
        break_node = ast.Break()
        res = self.visitor.visit(break_node)
        self.assertIsNone(res)


class TestLeanTranslatorAssert(TestTranslatorCoreBase):
    """アサーション文 (visit_Assert) のテスト"""

    def test_visit_assert_increment(self):
        """assert 文が訪問されるたびにラベル番号がインクリメントされること"""
        self.assertEqual(self.visitor.assert_count, 0)

        node1 = self.parse_stmt("assert x > 0")
        res1 = self.visitor.visit(node1)
        self.assertEqual(res1, "have h_assert_0 : (x > 0) := by sorry")
        self.assertEqual(self.visitor.assert_count, 1)

        node2 = self.parse_stmt("assert y < 10")
        res2 = self.visitor.visit(node2)
        self.assertEqual(res2, "have h_assert_1 : (y < 10) := by sorry")
        self.assertEqual(self.visitor.assert_count, 2)


class TestLeanTranslatorFunctionScope(TestTranslatorCoreBase):
    """関数スコープ管理 (visit_FunctionDef) のテスト"""

    def test_current_function_tracking_and_restoration(self):
        """visit_FunctionDef 実行中に current_function が更新され、終了時に復元されること"""
        self.assertIsNone(self.visitor.current_function)

        code = (
            "def outer(x: int) -> int:\n"
            "    return x"
        )
        node = self.parse_stmt(code)

        self.assertIsNone(self.visitor.current_function)
        res = self.visitor.visit(node)
        self.assertIsNone(self.visitor.current_function)
        self.assertIn("def outer (x : Int) : Int :=", res)


class TestLeanTranslatorForLoop(TestTranslatorCoreBase):
    """For ループの末尾再帰変換 (visit_For) のテスト"""

    def test_for_loop_outside_function_scope(self):
        """関数スコープ外（トップレベル）で for ループが存在する場合のエラー出力"""
        self.visitor.current_function = None
        code = (
            "for i in range(10):\n"
            "    balance += 1"
        )
        node = self.parse_stmt(code)
        res = self.visitor.visit(node)
        self.assertEqual(res, "-- [Unsupported] For: Loop outside of function scope")

    def test_for_loop_without_loop_info_unsupported(self):
        """解析情報の loop_info が登録されていない場合の未対応エラー"""
        self.visitor.current_function = "my_func"
        self.context.functions["my_func"] = {}
        code = (
            "for i in range(10):\n"
            "    balance += 1"
        )
        node = self.parse_stmt(code)
        res = self.visitor.visit(node)
        self.assertEqual(
            res,
            "-- [Unsupported] For: Only simple 'for i in range(n)' loops are supported for recursion conversion"
        )

    def test_for_loop_non_range_iter_unsupported(self):
        """range 以外のイテレータ（例: items リスト）が使われている場合のエラー"""
        self.visitor.current_function = "my_func"
        code = (
            "for item in items:\n"
            "    balance += item"
        )
        node = self.parse_stmt(code)
        self.context.functions["my_func"] = {
            "loop_info": [{"node": node, "state_vars": ["balance"]}]
        }
        res = self.visitor.visit(node)
        self.assertEqual(
            res,
            "-- [Unsupported] For: Only simple 'for i in range(n)' loops are supported for recursion conversion"
        )

    def test_for_loop_single_state_variable(self):
        """単一の状態変数を持つ for ループの let rec 変換"""
        self.visitor.current_function = "accumulate"
        code = (
            "for i in range(n):\n"
            "    balance += 10"
        )
        node = self.parse_stmt(code)
        self.context.functions["accumulate"] = {
            "loop_info": [{"node": node, "state_vars": ["balance"]}]
        }

        expected = (
            "let rec loop (n : Nat) (balance : Rat) : Rat :=\n"
            "  if n = 0 then balance\n"
            "  else\n"
            "        let balance := balance + 10;\n"
            "    loop (n - 1) balance\n"
            "  termination_by n\n"
            "let balance := loop (n).toNat balance;"
        )
        self.assertEqual(self.visitor.visit(node), expected)

    def test_for_loop_multiple_state_variables(self):
        """複数の状態変数を持つ for ループの let rec 変換"""
        self.visitor.current_function = "two_pointers"
        code = (
            "for i in range(steps):\n"
            "    x += 1\n"
            "    y += 2"
        )
        node = self.parse_stmt(code)
        self.context.functions["two_pointers"] = {
            "loop_info": [{"node": node, "state_vars": ["x", "y"]}]
        }

        expected = (
            "let rec loop (n : Nat) (x : Rat) (y : Rat) : (Rat × Rat) :=\n"
            "  if n = 0 then (x, y)\n"
            "  else\n"
            "        let x := x + 1;\n"
            "    let y := y + 2;\n"
            "    loop (n - 1) x y\n"
            "  termination_by n\n"
            "let (x, y) := loop (steps).toNat x y;"
        )
        self.assertEqual(self.visitor.visit(node), expected)


class TestLeanTranslatorHelpers(TestTranslatorCoreBase):
    """補助ヘルパーメソッド群のテスト"""

    def test_wrap(self):
        """_wrap による括弧付けの判定"""
        binop = self.parse_expr("a + b")
        call = self.parse_expr("f(x)")
        if_exp = self.parse_expr("1 if c else 2")
        name = self.parse_expr("x")
        const = self.parse_expr("100")

        self.assertEqual(self.visitor._wrap(binop), "(a + b)")
        self.assertEqual(self.visitor._wrap(call), "(f x)")
        self.assertEqual(self.visitor._wrap(if_exp), "(if c then 1 else 2)")
        self.assertEqual(self.visitor._wrap(name), "x")
        self.assertEqual(self.visitor._wrap(const), "100")

    def test_unsupported(self):
        """_unsupported による未対応メッセージのフォーマット"""
        node = ast.Break()
        res = self.visitor._unsupported(node, "Break is not supported")
        self.assertEqual(res, "-- [Unsupported] Break: Break is not supported")

    def test_extract_doc_and_body_with_docstring(self):
        """docstring を持つ関数からの doc と body の分離"""
        code = (
            "def foo():\n"
            "    \"\"\"This is docstring.\"\"\"\n"
            "    return 1"
        )
        node = self.parse_stmt(code)
        doc, stmts = self.visitor._extract_doc_and_body(node)
        self.assertEqual(doc, "This is docstring.")
        self.assertEqual(len(stmts), 1)
        self.assertIsInstance(stmts[0], ast.Return)

    def test_extract_doc_and_body_without_docstring(self):
        """docstring を持たない関数からの抽出"""
        code = (
            "def foo():\n"
            "    return 1"
        )
        node = self.parse_stmt(code)
        doc, stmts = self.visitor._extract_doc_and_body(node)
        self.assertIsNone(doc)
        self.assertEqual(len(stmts), 1)
        self.assertIsInstance(stmts[0], ast.Return)

    def test_format_args(self):
        """_format_args による引数リストのフォーマット"""
        code = "def sample(a: int, b: float, flag: bool): pass"
        node = self.parse_stmt(code)
        args_str = self.visitor._format_args(node.args)
        self.assertEqual(args_str, "(a : Int) (b : Rat) (flag : Bool)")

    def test_format_preconditions_standard(self):
        """通常関数の事前条件フォーマット"""
        cond = self.parse_expr("x > 0")
        self.context.functions["my_func"] = {"preconditions": [cond]}
        formatted = self.visitor._format_preconditions("my_func")
        self.assertEqual(formatted, "(h_precond_0 : (x > 0))")

    def test_format_preconditions_verify_prefix(self):
        """verify_ プレフィックス関数における被検証関数の事前条件参照"""
        cond1 = self.parse_expr("x > 0")
        cond2 = self.parse_expr("y > 0")
        self.context.functions["calculate"] = {"preconditions": [cond1, cond2]}
        formatted = self.visitor._format_preconditions("verify_calculate")
        self.assertEqual(formatted, "(h_precond_0 : (x > 0)) (h_precond_1 : (y > 0))")

    def test_format_preconditions_theorem_prefix(self):
        """theorem_ プレフィックス関数における被検証関数の事前条件参照"""
        cond = self.parse_expr("n >= 0")
        self.context.functions["fib"] = {"preconditions": [cond]}
        formatted = self.visitor._format_preconditions("theorem_fib")
        self.assertEqual(formatted, "(h_precond_0 : (n >= 0))")

    def test_build_function_or_theorem_def(self):
        """_build_function_or_theorem による関数 (def) 構築"""
        code = (
            "def compute(x: int) -> int:\n"
            "    \"\"\"Doc\"\"\"\n"
            "    assert x > 0\n"
            "    return x * 2"
        )
        node = self.parse_stmt(code)
        cond = node.body[1].test  # assert x > 0 の test ノード
        meta = {
            "preconditions": [cond],
            "hint": "x",
            "is_recursive": True,
        }
        self.context.functions["compute"] = meta
        res = self.visitor._build_function_or_theorem(
            node=node,
            args="(x : Int)",
            is_thm=False,
            meta=meta
        )
        self.assertIn("/-- Doc -/", res)
        self.assertIn("def compute (x : Int) (h_precond_0 : (x > 0)) : Int :=", res)
        self.assertIn("x * 2", res)
        self.assertIn("termination_by x", res)
        # 事前条件と重複する assert は本体から除外されていること
        self.assertNotIn("have h_assert_", res)

    def test_build_function_or_theorem_def_empty_body_sorry(self):
        """本体が事前条件の assert しかない場合、本体に sorry が補完されること"""
        code = (
            "def empty_fn(x: int) -> int:\n"
            "    assert x > 0"
        )
        node = self.parse_stmt(code)
        cond = node.body[0].test
        meta = {"preconditions": [cond]}
        self.context.functions["empty_fn"] = meta
        res = self.visitor._build_function_or_theorem(
            node=node,
            args="(x : Int)",
            is_thm=False,
            meta=meta
        )
        self.assertIn("def empty_fn (x : Int) (h_precond_0 : (x > 0)) : Int :=\n  sorry", res)

    def test_build_function_or_theorem_theorem(self):
        """_build_function_or_theorem による定理 (theorem) 構築"""
        code = (
            "def verify_test(x: int) -> bool:\n"
            "    assert x > 0\n"
            "    return x + 1 > 1"
        )
        node = self.parse_stmt(code)
        meta = {}
        res = self.visitor._build_function_or_theorem(
            node=node,
            args="(x : Int)",
            is_thm=True,
            meta=meta
        )
        expected = (
            "theorem verify_test (x : Int) : (x + 1 > 1) :=\n"
            "  have h_assert_0 : (x > 0) := by sorry\n"
            "  by sorry"
        )
        self.assertEqual(res, expected)

    def test_build_function_or_theorem_theorem_rfl_fallback(self):
        """定理の証明本体が Return 文のみの場合、証明に rfl が補完されること"""
        code = (
            "def verify_simple(x: int) -> bool:\n"
            "    return x == x"
        )
        node = self.parse_stmt(code)
        meta = {}
        res = self.visitor._build_function_or_theorem(
            node=node,
            args="(x : Int)",
            is_thm=True,
            meta=meta
        )
        expected = "theorem verify_simple (x : Int) : (x == x) :=\n  rfl"
        self.assertEqual(res, expected)

    def test_build_function_or_theorem_theorem_no_return_fallback_true(self):
        """定理の本体に Return 文がない場合、命題として True が設定されること"""
        code = (
            "def verify_no_ret(x: int) -> bool:\n"
            "    assert x > 0"
        )
        node = self.parse_stmt(code)
        meta = {}
        res = self.visitor._build_function_or_theorem(
            node=node,
            args="(x : Int)",
            is_thm=True,
            meta=meta
        )
        self.assertIn("theorem verify_no_ret (x : Int) : True :=", res)


if __name__ == "__main__":
    unittest.main()
