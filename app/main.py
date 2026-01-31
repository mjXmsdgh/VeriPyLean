import ast
import streamlit as st
import toLean


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
    }
]

# --- Streamlit UI 部分 ---
st.title("PyLean Prototype")
st.caption("PythonをLean 4へリアルタイム変換")

# セッション状態で入力コードを管理
if 'annotation' not in st.session_state:
    st.session_state.annotation = ""

# サイドバーにサンプルボタンを配置
st.sidebar.header("サンプル選択")
for sample in SAMPLES:
    if st.sidebar.button(sample["name"]):
        st.session_state.code_input = sample["code"]
        st.session_state.annotation = sample["annotation"]

col1, col2 = st.columns(2)

with col1:
    st.subheader("Python View")

    code_input = st.text_area("Pythonコードを入力してください", 
                               key="code_input", height=200)

with col2:
    st.subheader("Lean 4 View")
    try:
        # 入力を解析してAST（木構造）にする
        parsed_ast_root = ast.parse(code_input)
        if not parsed_ast_root.body:
            st.warning("コードが入力されていません。")
            st.stop()
        parsed_ast = parsed_ast_root.body[0]
        
        # Lean風のテキストに変換
        lean_code = toLean.translate_to_lean(parsed_ast)
        
        # 文字列操作が含まれる場合のみ、Pythonの挙動（+で結合）を再現するヘルパーを追加
        if "String" in lean_code or '"' in lean_code:
            preamble = "instance : Add String where add := String.append\n\n"
        else:
            preamble = ""

        # トップレベルのノードが関数定義なら、変換結果をそのまま使う
        # そうでなければ、ダミーの関数(example)でラップしてLeanの構文に合わせる
        if isinstance(parsed_ast, ast.FunctionDef):
            final_code = preamble + lean_code
        else:
            final_code = preamble + f"def example (n : Int) : Int :=\n  {lean_code}"

        st.code(final_code, language="lean")
        st.success("AST解析成功: 構文は正当です")

        # 注釈があれば表示
        if st.session_state.annotation:
            st.info(st.session_state.annotation)
        
    except Exception as e:
        st.error(f"解析エラー: {e}")
