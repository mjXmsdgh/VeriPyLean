# --- サンプルコードと解説の定義 ---
SAMPLES = [
    {
        "name": "算術演算の例",
        "category": "基本文法",
        "code": "def arithmetic_example(a, b, c):\n    return (a + b) * 2 - c",
        "annotation": """
        **解説：基本的な算術演算**

        Pythonの基本的な演算子（`+`, `-`, `*`）は、Lean 4の対応する演算子に直接変換されます。
        括弧による演算優先順位も正しく維持されます。
        """
    },
    {
        "name": "ローカル変数の定義",
        "category": "基本文法",
        "code": "def multiline_example(x: int, y: int) -> int:\n    sum_val = x + y\n    diff_val = x - y\n    return sum_val * diff_val",
        "annotation": """
        **解説：変数代入と let 式**

        Pythonの関数内での変数代入は、Leanの `let` 式に変換されます。
        
        Python: `sum_val = x + y`
        Lean: `let sum_val := x + y;`

        複数のステップを持つ計算を、中間変数を使って整理して記述できます。
        """
    },
    {
        "name": "条件式の例",
        "category": "基本文法",
        "code": "def conditional_example(n):\n    return n if n != 0 else 1",
        "annotation": """
        **解説：条件式（三項演算子）**

        Pythonの `x if condition else y` 形式の条件式は、Leanの `if condition then x else y` に変換されます。
        """
    },
    {
        "category": "基本文法",
        "annotation": """
        **解説：関数呼び出しの変換**

        Pythonの関数呼び出し `func(arg1, arg2)` は、Leanの関数適用構文 `func arg1 arg2` に変換されます。

        例:
        Python: `min(a, b)`
        Lean: `min a b`
        """,
        "code": "def call_example(a: int, b: int) -> int:\n    return min(a, b) + max(a, b)",
        "name": "関数の呼び出し"
    },
    {
        "name": "連結比較 (0 <= x < 10)",
        "category": "基本文法",
        "code": "def range_check(x: int) -> bool:\n    return 0 <= x < 10",
        "annotation": """
        **解説：連結比較演算子の展開**

        Python特有の `a < b < c` のような連結比較は、Leanの論理積 `(a < b) && (b < c)` に展開されます。
        """
    },
    {
        "name": "論理演算 (and, or, not)",
        "category": "基本文法",
        "code": "def logic_example(a: bool, b: bool, c: bool) -> bool:\n    return (a and b) or (not c)",
        "annotation": """
        **解説：論理演算子**

        Pythonの論理演算子（`and`, `or`, `not`）は、Lean 4の対応する演算子に変換されます。

        *   `and` -> `&&`
        *   `or` -> `||`
        *   `not` -> `!`
        """
    },
    {
        "name": "剰余演算と整数の性質",
        "category": "基本文法",
        "code": "def parity_check(n: int) -> bool:\n    is_even = (n % 2 == 0)\n    is_positive_odd = (n > 0) and (n % 2 != 0)\n    return is_even or is_positive_odd",
        "annotation": """
        **解説：剰余演算（%）と整数の比較**

        整数（`int`）に対する剰余演算 `%` は、Lean 4の `%` 演算子にマッピングされます。
        これを利用して、偶数・奇数の判定や、倍数のチェックなどの性質を記述できます。

        Python: `n % 2 == 0`
        Lean: `n % 2 == 0`

        比較演算子（`==`, `!=`, `>`, `<`）も同様に変換され、複数の論理条件を組み合わせることも可能です。
        
        ※注意：負の数に対する剰余の挙動はPythonとLeanで異なる場合があるため、形式検証の際は定義の確認が重要です。
        """
    },
    {
        "name": "割り算と型キャスト",
        "category": "基本文法",
        "code": "def div_example(a: int, b: int) -> float:\n    return a / b",
        "annotation": """
        **解説：割り算の挙動**

        Pythonの `/` 演算子は常に浮動小数点数を返すため、Lean側でも強制的に `Float` として計算するように変換します。

        変換結果: `((a : Float) / (b : Float))`
        """
    },
    {
        "name": "リスト内包表記の例",
        "category": "データ構造",
        "code": "def double_evens(numbers: list) -> list:\n    # 偶数のみを2倍する\n    return [n * 2 for n in numbers if n % 2 == 0]",
        "annotation": """
        **解説：リスト内包表記の変換**

        Pythonのリスト内包表記は、Leanの `map` や `filterMap` 関数に変換されます。

        *   `[f(x) for x in xs]` は `xs.map (fun x => f(x))` になります。
        *   `if` 条件を含む `[f(x) for x in xs if cond(x)]` は、より効率的な `xs.filterMap (fun x => if cond(x) then some (f(x)) else none)` に変換されます。
        """
    },
    {
        "name": "リスト集計 (sum, len)",
        "category": "データ構造",
        "code": "def calculate_average(numbers: list) -> float:\n    count = len(numbers)\n    if count == 0:\n        return 0.0\n    \n    total = sum(numbers)\n    return total / count",
        "annotation": """
        **解説：リスト集計関数の変換**

        Pythonの組み込み関数 `sum()` と `len()` は、Leanのリスト操作関数に変換されます。

        *   `sum(list)` は、内部で型クラスを応用した `py_sum list` に変換され、`Int` や `Float` など様々な型のリストに対応します。
        *   `len(list)` は、Lean標準の `List.length list` に変換されます。

        この例のように、リストの合計や平均を計算するロジックを記述できます。
        """
    },
    {
        "name": "タプルの例",
        "category": "データ構造",
        "code": "def tuple_literal_example():\n    return (1, \"two\")",
        "annotation": """
        **解説：タプルリテラルの変換**

        Pythonのタプルリテラル `(1, "two")` は、Leanのタプル `(1, "two")` に変換されます。

        **現在の制約:**
        現在は戻り値の型推論に制限があるため、複雑なタプルでは手動で型調整が必要な場合があります。
        """
    }
    ,
    {
        "name": "Decimal型の例",
        "category": "応用（金融・計算）",
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
        "category": "応用（金融・計算）",
        "code": "from decimal import Decimal\nimport math\n\ndef calculate_tax_floor(price: Decimal, rate: Decimal) -> int:\n    # 消費税計算（切り捨て）\n    tax = price * rate\n    return math.floor(tax)\n\ndef calculate_tax_round(price: Decimal, rate: Decimal) -> int:\n    # 消費税計算（四捨五入・偶数丸め）\n    tax = price * rate\n    return round(tax)",
        "annotation": """
        **解説：Decimal型による厳密な端数処理**

        金融計算では、浮動小数点数（Float）の誤差が許されないため、`Decimal` 型（Leanでは `Rat`）を使用します。

        *   **切り捨て**: `math.floor()` は、Leanの `Rat.floor` に変換され、小数点以下を切り捨てて整数 (`Int`) を返します。
        *   **丸め**: `round()` は、Leanの `Rat.round` に変換されます。これはPython 3の仕様に合わせて「偶数丸め（銀行丸め）」として実装されています。

        例: `2.5` -> `2`, `3.5` -> `4`
        """
    },
    {
        "name": "日付計算（Actual/365）",
        "category": "応用（金融・計算）",
        "code": "from datetime import date\n\ndef day_count_act365(start: date, end: date) -> float:\n    # 日付の差分（期間）を計算\n    delta = end - start\n    # 日数 / 365.0 で年換算\n    return delta.days / 365.0",
        "annotation": """
        **解説：日付計算と構造体**

        Pythonの `datetime.date` は Leanの `Date` 構造体に変換されます。
        
        `end - start` のような日付の引き算は、Lean上で `TimeDelta` 構造体を返すように定義されており、`.days` フィールドで日数差を取得できます。
        """
    },
    {
        "name": "複利計算（Decimal, 累乗）",
        "category": "応用（金融・計算）",
        "code": """from decimal import Decimal

def compound_interest(principal: Decimal, rate: Decimal, years: int) -> Decimal:
    # 複利計算: 元本 * (1 + 利率) ^ 年数
    return principal * (1 + rate) ** years""",
        "annotation": """
        **解説：金融計算と累乗**

        金融計算で重要な複利計算も、PyLeanで扱うことができます。

        *   **`Decimal` -> `Rat`**: `Decimal`型はLeanの有理数(`Rat`)に変換され、計算誤差を防ぎます。
        *   **`**` -> `^`**: Pythonの累乗演算子 `**` は、Leanの `^` 演算子に正しく変換されます。

        これにより、`元本 * (1 + 利率) ^ 年数` のような数式を直接的かつ安全に表現できます。
        """
    },
    {
        "name": "再帰関数（停止性証明）",
        "category": "高度な機能（再帰・証明）",
        "code": """def factorial(n: int) -> int:
    if n == 0:
        return 1
    else:
        return n * factorial(n - 1)""",
        "annotation": """
        **解説：再帰関数の停止性証明**

        Pythonの再帰関数は、Leanの再帰関数に変換されます。
        Leanでは、再帰関数が必ず停止する（無限ループにならない）ことを証明する必要があります。

        この例では、再帰呼び出し `factorial(n - 1)` で引数 `n` が減少していることをPyLeanが自動で検出し、Leanコードに `termination_by n` という句を追加して停止性を証明します。
        """
    },
    {
        "name": "再帰関数（複雑なケース）",
        "category": "高度な機能（再帰・証明）",
        "code": """def ackermann(m: int, n: int) -> int:
    if m == 0:
        return n + 1
    elif n == 0:
        return ackermann(m - 1, 1)
    else:
        return ackermann(m - 1, ackermann(m, n - 1))""",
        "annotation": """
        **解説：複雑な再帰と停止性**

        アッカーマン関数のように、複数の引数にまたがる複雑な再帰や、引数が単純に減少しないケースでは、PyLeanは停止性を自動で証明できません。

        その場合、警告コメントが生成され、手動で `termination_by` 句を記述する必要があることを示します。
        この例では `termination_by m n` のように、辞書式順序で引数が減少することを手動で指定する必要があります。
        """
    },
    {
        "name": "型安全性（エラーの事前検知）",
        "category": "高度な機能（再帰・証明）",
        "code": 'def type_error_example():\n    return "hello" + 5',
        "annotation": """
        **解説：Leanによる強力な型チェック**

        このコードは、Pythonでは実行時に `TypeError` となりますが、構文自体は有効です。

        PyLeanで変換されたLeanコード `("hello" + 5)` では、コンパイラが「文字列と整数の足し算は不可能」と判断し、**実行前にエラーを報告**します。
        """
    },
    {
        "name": "（未サポート）forループ",
        "category": "制限事項",
        "code": "def sum_with_for_loop(numbers: list) -> int:\n    total = 0\n    for x in numbers:\n        total = total + x\n    return total",
        "annotation": """**解説：forループの変換について**

現在、Pythonの命令的な `for` ループ（特に、ループ外の変数を更新するようなケース）からLeanの関数型コード（`fold` や再帰）への自動変換はサポートされていません。

このような集計処理は、代わりに `sum()` 関数やリスト内包表記を使って表現することで、Leanに変換可能になります。

例： `return sum(numbers)`"""
    }
    ,
    {
        "name": "段階的所得税の計算（elif）",
        "category": "制御構造",
        "code": "def calculate_tax(income: int) -> int:\n    \"\"\"簡易的な所得税計算\"\"\"\n    if income <= 2000:\n        return 0\n    elif income <= 5000:\n        return (income - 2000) * 0.1\n    else:\n        return 300 + (income - 5000) * 0.2",
        "annotation": """
        **解説：複数分岐 (elif) と有理数計算の検証**

        この例は、複数の `elif` を含む複雑な制御フローと、小数が混在する計算の変換をテストします。

        *   **構文変換**: Python のネストされた `if` を、Lean のフラットな `else if` 構文へ正確にマッピングします。
        *   **数値の厳密性**: `0.1` などのリテラルは自動的に `(1/10 : Rat)` として扱われ、計算誤差を排除します。
        *   **論理チェック**: `SafetyAnalyzer` により、条件の順序が正しいか、網羅性が保たれているかが静的に解析されます。
        """
    },
    {
        "name": "安全性のチェックと検証（Assert文）",
        "category": "制御構造",
        "code": "def safe_division_rate(amount: float, divisor: float) -> float:\n    \"\"\"ゼロ除算を防ぐガード付きの計算\"\"\"\n    assert divisor > 0\n    return amount / divisor\n\ndef verify_safe_division_rate(amount: float, divisor: float):\n    return safe_division_rate(amount, divisor) == amount / divisor",
        "annotation": """
        **解説：Assert文による前提条件（事前条件）の検証**

        Pythonの `assert` 文を用いた前提条件（ゼロ除算防止、利率がマイナスにならない、期間が0以上など）を Lean 4 に変換・検証します。

        *   **事前条件の自動抽出**: 関数の引数に対する `assert divisor > 0` を解析し、Leanの関数定義の引数 `(h_precond_0 : divisor > 0)` にリフトします。
        *   **定理への証明引き継ぎ**: 検証用の定理 `verify_safe_division_rate` においても、同じ前提条件が自動的に引数として追加されます。
        *   **安全な呼び出しの検証**: 定理の中で `safe_division_rate` を呼び出す際、前提条件の証明引数 `h_precond_0` が自動的に渡されることで、数学的な安全性が保証されます。
        """
    }
]