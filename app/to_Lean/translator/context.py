import ast
from ..emitter import LeanEmitter

class TranslationContext:
    """
    翻訳プロセス全体のデータと状態を管理するコンテキストクラス。

    役割:
    - 翻訳中に発生した警告(warnings)やエラー(errors)の蓄積と保持。
    - 関数、クラス、型情報のシンボルテーブルとしての機能。
    - 解析フェーズ(SafetyAnalyzer)と生成フェーズ(LeanTranslator)の間での情報共有。
    - LeanEmitterのインスタンスを保持し、コード生成の土台を提供する。
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