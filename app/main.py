import streamlit as st
import toLean
import samples

# --- 描画ロジックの分離 ---
def render_lean_view(code_input):
    st.subheader("Lean 4 View")
    try:
        # 変換ロジック呼び出し（UI非依存）
        final_code = toLean.compile_python_to_lean(code_input)

        st.code(final_code, language="lean")
        st.success("AST解析成功: 構文は正当です")

        # 注釈があれば表示
        if st.session_state.annotation:
            st.info(st.session_state.annotation)
        
    except ValueError as e:
        st.warning(str(e))
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
