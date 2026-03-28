import ast
from . import translator
from . import preamble

def compile_python_to_lean(code_input):
    """Pythonコード文字列を受け取り、完全なLeanコード文字列を返す"""
    try:
        parsed_ast_root = ast.parse(code_input)
    except SyntaxError as e:
        raise ValueError(f"構文エラー: {e}")

    if not parsed_ast_root.body:
        raise ValueError("コードが入力されていません。")
    
    # 複数のステートメント（関数定義など）を処理し、import文は無視する
    lean_parts = []
    has_top_level_def = False
    
    for node in parsed_ast_root.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Assert):
            lean_parts.append(f"example : {translator.translate_to_lean(node.test)} := by\n  sorry")
            continue
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            has_top_level_def = True
        lean_parts.append(translator.translate_to_lean(node))
    
    lean_code = "\n\n".join(lean_parts)
    # 必要なヘルパー定義（プリアンブル）を構築
    preamble_code = preamble.generate(lean_code)

    if has_top_level_def:
        return preamble_code + lean_code
    else:
        return preamble_code + f"def example (n : Int) : Int :=\n  {lean_code}"