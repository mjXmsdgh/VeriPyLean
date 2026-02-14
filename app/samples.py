# --- サンプルコードと解説の定義 ---
SAMPLES = [
    {
        "name": "算術演算の例",
        "code": "def arithmetic_example(a, b, c):\n    return (a + b) * 2 - c",
        "annotation": ""
    },
    {
        "name": "条件式の例",
        "code": "def conditional_example(n):\n    return n if n != 0 else 1",
        "annotation": ""
    },
    {
        "name": "型エラーの例",
        "code": 'def type_error_example():\n    return "hello" + 5',
        "annotation": """
        **解説：なぜこれがLean 4でエラーになるのか**

        このコードは、Pythonでは実行時に `TypeError` となりますが、構文自体は有効です。

        一方、正しく変換されたLean 4コード `("hello" + 5)` では、`String`型（文字列）と `Int`型（整数）の間で `+` 演算が定義されていないため、型エラーとしてコンパイル前に検出されます。

        これは、変換プログラムの不具合ではなく、**Lean 4の厳密な型システムによるもの**です。これにより、実行前にバグを発見できます。
        """
    },
    {
        "name": "型ヒントの例",
        "code": 'def add_strings(a: str, b: str) -> str:\n    return a + b',
        "annotation": """
        **解説：Pythonの型ヒントの活用**

        Pythonの型ヒント（例: `a: str`, `-> str`）を読み取り、Lean 4の型定義（`a : String`, `: String`）に自動的に変換します。

        これにより、より正確で安全なコードを生成できます。型ヒントがない場合は、デフォルトで `Int` 型が使用されます。
        """
    }
    ,
    {
        "name": "リストの例",
        "code": "def list_literal_example() -> list:\n    return [10, 20, 30]",
        "annotation": """
        **解説：リストリテラルの変換**

        Pythonのリストリテラル `[10, 20, 30]` は、Leanのリストリテラル `[10, 20, 30]` に直接変換されます。

        返り値の型ヒント `-> list` を用いることで、Leanでの関数の返り値の型が `List Int` であることを示しています。
        """
    },
    {
        "name": "タプルの例",
        "code": "def tuple_literal_example():\n    return (1, \"two\")",
        "annotation": """
        **解説：タプルリテラルの変換**

        Pythonのタプルリテラル `(1, "two")` は、Leanのタプル `(1, "two")` に変換されます。

        **現在の制約:**
        現在のバージョンでは、タプルの型（例: `Int × String`）を自動で推論して関数の返り値の型に設定する機能は実装されていません。そのため、返り値の型がデフォルトの `Int` となり、生成されたLeanコードは型エラーになります。これは今後の改善点です。
        """
    },
    {
        "name": "複数行の例",
        "code": "def multiline_example(x: int, y: int) -> int:\n    sum_val = x + y\n    diff_val = x - y\n    return sum_val * diff_val",
        "annotation": """
        **解説：複数行ステートメントと変数定義**

        関数内の代入文は Lean の `let` 式に変換されます。
        
        Python:
        ```python
        sum_val = x + y
        ```
        Lean:
        ```lean
        let sum_val := (x + y);
        ```
        """
    },
    {
        "name": "関数呼び出しの例",
        "code": "def call_example(a: int, b: int) -> int:\n    return min(a, b) + max(a, b)",
        "annotation": """
        **解説：関数呼び出しの変換**

        Pythonの関数呼び出し `func(arg1, arg2)` は、Leanの関数適用構文 `func arg1 arg2`（スペース区切り）に変換されます。

        例:
        Python: `min(a, b)`
        Lean: `min a b`

        引数が式の場合は、結合順序を保つために自動的に括弧で囲まれます。
        """
    },
    {
        "name": "割り算（Float）の例",
        "code": "def div_example(a: int, b: int) -> float:\n    return a / b",
        "annotation": """
        **解説：割り算の挙動**

        Pythonの `/` 演算子は常に浮動小数点数を返すため、Lean側でも強制的に `Float` として計算するように変換します。

        変換結果: `((a : Float) / (b : Float))`

        注意: 返り値の型ヒント `-> float` が重要です。これがないとデフォルトの `Int` が返り値の型となり、計算結果（Float）との型不一致エラーが発生します。
        """
    }
    ,
    {
        "name": "連結比較の例",
        "code": "def range_check(x: int) -> bool:\n    return 0 <= x < 10",
        "annotation": """
        **解説：連結比較演算子の展開**

        Python特有の `a < b < c` のような連結比較は、Leanの論理積 `(a < b) && (b < c)` に展開されます。

        例:
        Python: `0 <= x < 10`
        Lean: `(0 <= x) && (x < 10)`
        """
    }
    ,
    {
        "name": "Decimal型の例",
        "code": "def decimal_example() -> Decimal:\n    # 浮動小数点数では 0.1 + 0.2 != 0.3 ですが、\n    # Decimal (Leanでは Rat) なら正確に計算できます。\n    return Decimal('0.1') + Decimal('0.2')",
        "annotation": """
        **解説：Decimal型（固定小数点・有理数）のサポート**

        Pythonの `decimal.Decimal` は、Leanの `Rat`（有理数）型にマッピングされます。
        
        `Decimal('0.1')` のようなコンストラクタ呼び出しは、自動的に `(1/10 : Rat)` という有理数リテラルに変換されます。
        これにより、金融計算などで重要な「丸め誤差のない正確な計算」がLean上で検証可能になります。
        """
    },
    {
        "name": "消費税計算（Decimal）",
        "code": "from decimal import Decimal\nimport math\n\ndef calculate_tax_floor(price: Decimal, rate: Decimal) -> int:\n    # 消費税計算（切り捨て）\n    tax = price * rate\n    return math.floor(tax)\n\ndef calculate_tax_round(price: Decimal, rate: Decimal) -> int:\n    # 消費税計算（四捨五入・偶数丸め）\n    tax = price * rate\n    return round(tax)",
        "annotation": """
        **解説：Decimal型による厳密な端数処理**

        金融計算では、浮動小数点数（Float）の誤差が許されないため、`Decimal` 型（Leanでは `Rat`）を使用します。

        *   **切り捨て**: `math.floor()` は、Leanの `Rat.floor` に変換され、小数点以下を切り捨てて整数 (`Int`) を返します。
        *   **丸め**: `round()` は、Leanの `Rat.round` に変換されます。これはPython 3の仕様に合わせて「偶数丸め（銀行丸め）」として実装されています。

        例: `2.5` -> `2`, `3.5` -> `4`
        """
    }
]