import ast
import streamlit as st

# --- 変換ロジック (ルールベースの核) ---
def translate_to_lean(node):
    if node is None:
        return ""

    # 数値
    if isinstance(node, ast.Constant):
        return str(node.value)
    
    # 変数
    elif isinstance(node, ast.Name):
        return node.id
    
    # Return文（中身をさらに解析）
    elif isinstance(node, ast.Return):
        return translate_to_lean(node.value)

    # 二項演算 (// や + など)
    elif isinstance(node, ast.BinOp):
        left = translate_to_lean(node.left)
        right = translate_to_lean(node.right)
        if isinstance(node.op, (ast.Div, ast.FloorDiv)):
            return f"({left} / {right})"
        elif isinstance(node.op, ast.Add):
            return f"({left} + {right})"
        elif isinstance(node.op, ast.Sub):
            return f"({left} - {right})"

    # 条件分岐
    elif isinstance(node, ast.If):
        test = translate_to_lean(node.test)
        # 0番目の要素を再帰的に変換
        body = translate_to_lean(node.body[0]) 
        orelse = translate_to_lean(node.orelse[0]) if node.orelse else "0"
        return f"if {test} then {body} else {orelse}"

    # 比較 (b != 0)
    elif isinstance(node, ast.Compare):
        left = translate_to_lean(node.left)
        op = "≠" if isinstance(node.ops[0], ast.NotEq) else "=="
        right = translate_to_lean(node.comparators[0])
        return f"{left} {op} {right}"
    


# --- Streamlit UI 部分 ---
st.title("PyLean Prototype")
st.caption("PythonをLean 4へリアルタイム変換")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Python View")
    code_input = st.text_area("Pythonコードを入力してください", 
                               value="return n + 5", height=200)

with col2:
    st.subheader("Lean 4 View")
    try:
        # 入力を解析してAST（木構造）にする
        # evalモードで簡易的に式としてパース
        parsed_ast = ast.parse(code_input).body[0]
        
        # Lean風のテキストに変換
        lean_code = translate_to_lean(parsed_ast)
        
        st.code(f"def example (n : Int) : Int :=\n  {lean_code}", language="lean")
        st.success("AST解析成功: 構文は正当です")
        
    except Exception as e:
        st.error(f"解析エラー: {e}")
