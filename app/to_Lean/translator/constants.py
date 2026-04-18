import ast

# --- 宣言的なマッピングの定義 ---

BIN_OPS = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.FloorDiv: "/",
    ast.Mod: "%",
    ast.Pow: "^",
}

COMP_OPS = {
    ast.Eq: "==",
    ast.NotEq: "≠",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
}

BOOL_OPS = {
    ast.And: "&&",
    ast.Or: "||",
}

UNARY_OPS = {
    ast.Not: "!",
    ast.USub: "-",
}

# --- テンプレート定義 ---

DOC_TEMPLATE = "/-- {doc} -/"
IND_HEADER = "inductive {name} where"
STRUCT_HEADER = "structure {name} where"
DERIVING_FOOTER = "deriving Repr, BEq"

DEF_HEADER = "def {name} {args} : {ret_type} :="
THM_HEADER = "theorem {name} {args} : {prop} :="
THM_PROOF = "by sorry"
TERMINATION_BY = "termination_by {hint}"
REC_WARN = "-- [PyLean] Warning: No termination measure found.\n{code}"