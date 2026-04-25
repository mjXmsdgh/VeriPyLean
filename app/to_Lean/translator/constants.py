import ast

# Lean 4 の演算子へのマッピング
BIN_OPS = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Div: "/",
    ast.FloorDiv: "/",
    ast.Mod: "%",
    ast.Pow: "^",
}

UNARY_OPS = {
    ast.UAdd: "+",
    ast.USub: "-",
    ast.Not: "!",
}

BOOL_OPS = {
    ast.And: "&&",
    ast.Or: "||",
}

COMP_OPS = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
}

DOC_TEMPLATE = "/-- {doc} -/"