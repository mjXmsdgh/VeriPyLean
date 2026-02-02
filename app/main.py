import ast
import streamlit as st
import toLean
import samples

# --- 描画ロジックの分離 ---
def render_lean_view(code_input):
    st.subheader("Lean 4 View")
    try:
        # 入力を解析してAST（木構造）にする
        parsed_ast_root = ast.parse(code_input)
        if not parsed_ast_root.body:
            st.warning("コードが入力されていません。")
            return
        parsed_ast = parsed_ast_root.body[0]
        
        # Lean風のテキストに変換
        lean_code = toLean.translate_to_lean(parsed_ast)
        
        # 必要なヘルパー定義（プリアンブル）を構築
        preamble_parts = []

        # 文字列結合 (+) のサポート
        if "String" in lean_code or '"' in lean_code:
            preamble_parts.append("instance : Add String where add := String.append")
        
        # Float除算のための Int -> Float 自動型変換サポート
        if "Float" in lean_code:
            preamble_parts.append("instance : Coe Int Float where coe := Int.toFloat")

        # 除算 (/) のためのヘルパー型クラス定義
        # Pythonの / は Int/Int->Float, Float/Float->Float, Decimal/Decimal->Decimal (Rat) となる
        preamble_parts.append("""class PyDiv (α : Type) (β : outParam Type) where
  py_div : α -> α -> β

instance : PyDiv Int Float where py_div a b := (a : Float) / (b : Float)
instance : PyDiv Float Float where py_div a b := a / b
instance : PyDiv Rat Rat where py_div a b := a / b""")

        preamble = "\n\n".join(preamble_parts) + ("\n\n" if preamble_parts else "")

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

# --- Streamlit UI 部分 ---
st.title("PyLean Prototype")
st.caption("PythonをLean 4へリアルタイム変換")

# セッション状態で入力コードを管理
if 'annotation' not in st.session_state:
    st.session_state.annotation = ""

# サイドバーにサンプルボタンを配置
st.sidebar.header("サンプル選択")
for sample in samples.SAMPLES:
    if st.sidebar.button(sample["name"]):
        st.session_state.code_input = sample["code"]
        st.session_state.annotation = sample["annotation"]

col1, col2 = st.columns(2)

with col1:
    st.subheader("Python View")

    code_input = st.text_area("Pythonコードを入力してください", 
                               key="code_input", height=200)

with col2:
    render_lean_view(code_input)
