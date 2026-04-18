import ast
from ... import types

def extract_doc_and_body(node):
    """ノードからdocstringを除去した本体ステートメントを返す"""
    doc = ast.get_docstring(node)
    stmts = node.body
    if doc and stmts and isinstance(stmts[0], ast.Expr):
        stmts = stmts[1:]
    return doc, stmts

def format_args(args_node, context):
    """関数引数を (name : Type) の形式で結合する"""
    return " ".join([f"({a.arg} : {types.translate_type(a.annotation, context)})" for a in args_node.args])

def get_block_lines(v, stmts, is_theorem=False):
    """複数のステートメントを変換し、行のリストとして返す"""
    if not stmts:
        return ["()" if not is_theorem else "True"]
    
    lines = []
    for i, stmt in enumerate(stmts):
        lines.append(v._v(stmt))
        if i == len(stmts) - 1:
            if isinstance(stmt, (ast.Assign, ast.Assert)):
                lines.append("()" if not is_theorem else "True")
    return lines