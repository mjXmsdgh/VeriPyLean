import ast
from ... import types
from .utils import extract_doc_and_body, format_args, get_block_lines

def handle_function_def(node, v):
    """関数・定理定義の変換をハンドリングする"""
    doc, stmts = extract_doc_and_body(node)
    args = format_args(node.args, v.context)
    is_thm = node.name.startswith(("verify_", "theorem_"))
    meta = v.context.functions.get(node.name, {})
    
    is_ret = is_thm and isinstance(stmts[-1], ast.Return)
    body_stmts = stmts[:-1] if is_ret else stmts
    
    if is_thm:
        prop = v._v(stmts[-1].value) if is_ret else "True"
        body_lines = get_block_lines(v, body_stmts, is_theorem=True)
        return v.emitter.format_theorem(node.name, args, prop, body_lines, doc=doc)
    else:
        ret_type = types.translate_type(node.returns, v.context)
        body_lines = get_block_lines(v, body_stmts, is_theorem=False)
        return v.emitter.format_function(
            node.name, args, ret_type, body_lines, 
            doc=doc, termination_hint=meta.get("hint"), is_recursive=meta.get("is_recursive")
        )

def handle_class_def(node, v):
    """クラス定義（Enum/Structure）をハンドリングする"""
    kind = v.context.classes.get(node.name)
    if kind == "enum":
        variants = [t.id for s in node.body if isinstance(s, ast.Assign) for t in s.targets if isinstance(t, ast.Name)]
        return v.emitter.format_inductive(node.name, variants)
    
    if kind == "structure":
        fields = []
        for s in node.body:
            if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name):
                fields.append((s.target.id, types.translate_type(s.annotation, v.context)))
        return v.emitter.format_structure(node.name, fields)
    
    return v._unsupported(node, "Only Enums and @dataclass are supported")