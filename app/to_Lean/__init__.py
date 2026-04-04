import ast
from . import translator

def compile_python_to_lean(code: str):
    """
    Pythonソースコードを受け取り、Lean 4コードと警告リストを返すメインエントリポイント。
    """
    try:
        tree = ast.parse(code)
        context = translator.analyze(tree)
        lean_code = translator.translate_to_lean(tree, context)
        return lean_code, context.warnings
    except Exception as e:
        # パースエラー等の致命的なエラー時のハンドリング
        return f"-- Error during translation: {str(e)}", [str(e)]

def analyze(node):
    """下位互換性のために維持: ASTの解析を行う"""
    return translator.analyze(node)

def translate_to_lean(node, context=None):
    """下位互換性のために維持: ASTをLeanコードに変換する"""
    return translator.translate_to_lean(node, context)