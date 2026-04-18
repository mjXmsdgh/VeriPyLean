from contextlib import contextmanager

class CodeBuilder:
    """インデント管理を行いながら構造的なコード文字列を組み立てるクラス"""
    def __init__(self, indent_size=2):
        self.lines = []
        self.level = 0
        self.indent_size = indent_size

    def indent(self):
        """インデントレベルを1つ上げる"""
        self.level += 1
    def dedent(self):
        """インデントレベルを1つ下げる"""
        self.level = max(0, self.level - 1)

    def add(self, text):
        """現在のインデントを付与して1行追加する"""
        prefix = " " * (self.level * self.indent_size)
        self.lines.append(f"{prefix}{text}")

    @contextmanager
    def block(self, header):
        """ヘッダーを追加し、コンテキスト内をインデントブロックとする"""
        self.add(header)
        self.indent()
        yield
        self.dedent()

    def build(self): return "\n".join(self.lines)

class TranslationContext:
    """変換プロセス全体で共有されるコンテキスト（関数情報、クラス情報、警告ログ）"""
    def __init__(self):
        self.functions = {}  # name -> {"is_recursive": bool, "hint": str}
        self.classes = {}    # name -> "enum" | "structure"
        self.warnings = []

    def add_warning(self, node, message):
        """解析・変換中に発生した制限事項やエラーを警告として記録する"""
        line = getattr(node, 'lineno', 'unknown')
        col = getattr(node, 'col_offset', 'unknown')
        self.warnings.append(f"Line {line}, Col {col}: {message}")