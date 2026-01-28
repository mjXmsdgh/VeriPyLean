import ast
import streamlit as st
import toLean


# --- Streamlit UI 部分 ---
st.title("PyLean Prototype")
st.caption("PythonをLean 4へリアルタイム変換")

# セッション状態で入力コードを管理
if 'code_input' not in st.session_state:
    st.session_state.code_input = "return n + 5"
if 'annotation' not in st.session_state:
    st.session_state.annotation = ""

col1, col2 = st.columns(2)

with col1:
    st.subheader("Python View")

    st.write("サンプル:")
    b_col1, b_col2, b_col3, _ = st.columns([1, 1, 1, 1])
    if b_col1.button("算術演算の例"):
        st.session_state.code_input = "def arithmetic_example(a, b, c):\n    return (a + b) * 2 - c"
        st.session_state.annotation = ""
    if b_col2.button("条件式の例"):
        st.session_state.code_input = "def conditional_example(n):\n    return n if n != 0 else 1"
        st.session_state.annotation = ""
    if b_col3.button("型エラーの例"):
        st.session_state.code_input = 'def type_error_example():\n    return "hello" + 5'
        st.session_state.annotation = """
        **解説：なぜこれがLean 4でエラーになるのか**

        このコードは、Pythonでは実行時に `TypeError` となりますが、構文自体は有効です。

        一方、正しく変換されたLean 4コード `("hello" + 5)` では、`String`型（文字列）と `Int`型（整数）の間で `+` 演算が定義されていないため、型エラーとしてコンパイル前に検出されます。

        これは、変換プログラムの不具合ではなく、**Lean 4の厳密な型システムによるもの**です。これにより、実行前にバグを発見できます。
        """

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
        
        # トップレベルのノードが関数定義なら、変換結果をそのまま使う
        if isinstance(parsed_ast, ast.FunctionDef):
            st.code(lean_code, language="lean")
        else:
            st.code(f"def example (n : Int) : Int :=\n  {lean_code}", language="lean")
        st.success("AST解析成功: 構文は正当です")

        # 注釈があれば表示
        if st.session_state.annotation:
            st.info(st.session_state.annotation)
        
    except Exception as e:
        st.error(f"解析エラー: {e}")
