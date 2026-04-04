import ast
from .analysis import analyze as _analyze_ast
from .context import TranslationContext, CodeBuilder
from .core import LeanTranslator

def analyze(node):
    """
    ASTを走査して、型定義や再帰構造などの変換に必要なメタデータを収集する。
    """
    context = TranslationContext()
    return _analyze_ast(node, context)

def translate_to_lean(node, context=None):
    """
    Python ASTノードを対応するLean 4コード文字列に変換するエントリポイント。
    """
    if node is None:
        return ""
    if context is None:
        # 個別ノードの変換でも最小限の解析を行う
        context = analyze(node)
    
    translator = LeanTranslator(context)
    return translator.visit(node)