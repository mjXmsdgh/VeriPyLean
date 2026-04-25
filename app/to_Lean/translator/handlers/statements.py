import ast
from ... import types

def handle_if(node, v):
    """If文をLeanの if then else 構文に変換する"""
    return v.emitter.format_if_stmt(
        v._v(node.test),
        [v._v(s) for s in node.body],
        [v._v(s) for s in node.orelse] if node.orelse else ["0"]
    )

def handle_function_def(node, v):
    """関数定義をLeanの def または theorem に変換する"""
    doc, stmts = v._extract_doc_and_body(node)
    args = v._format_args(node.args)
    is_thm = node.name.startswith(("verify_", "theorem_"))
    # context に保持されているメタ情報を取得
    meta = getattr(v.context, 'functions', {}).get(node.name, {})
    return v._build_function_or_theorem(node, doc, stmts, args, is_thm, meta)

def handle_class_def(node, v):
    """クラス定義（EnumやDataclass）をLeanの inductive または structure に変換する"""
    kind = getattr(v.context, 'classes', {}).get(node.name)
    if kind == "enum":
        variants = [t.id for s in node.body if isinstance(s, ast.Assign) 
                    for t in s.targets if isinstance(t, ast.Name)]
        return v.emitter.format_inductive(node.name, variants)
    if kind == "structure":
        fields = [(s.target.id, types.translate_type(s.annotation)) 
                  for s in node.body if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name)]
        return v.emitter.format_structure(node.name, fields)
    return v._unsupported(node, "Only Enums and @dataclass are supported")