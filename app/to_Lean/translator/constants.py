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

IND_TEMPLATE = """inductive {name} where
{items}
deriving Repr, BEq"""

STRUCT_TEMPLATE = """structure {name} where
{items}
deriving Repr, BEq"""