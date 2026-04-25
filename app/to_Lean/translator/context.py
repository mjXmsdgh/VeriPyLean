import ast
from ..emitter import LeanEmitter

class TranslationContext:
    """
    翻訳プロセス全体で共有されるコンテキスト情報を保持するクラス。
    警告、エラー、型情報などを管理する。
    """
    def __init__(self):
        self.warnings = []
        self.errors = []
        self.functions = {}
        self.classes = {}
        self.emitter = LeanEmitter(self) # LeanEmitter は context を必要とする
        # 今後、型情報、変数スコープ、ユーザー定義型などの情報をここに追加する

    def add_warning(self, node: ast.AST, message: str):
        self.warnings.append(f"Warning at line {node.lineno}: {message}")