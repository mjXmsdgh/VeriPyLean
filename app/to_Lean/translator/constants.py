from __future__ import annotations

import ast

# Lean 4 の演算子へのマッピング
BIN_OPS: dict[type[ast.operator], str] = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Div: "/",
    ast.FloorDiv: "/",
    ast.Mod: "%",
    ast.Pow: "^",
}

UNARY_OPS: dict[type[ast.unaryop], str] = {
    ast.UAdd: "+",
    ast.USub: "-",
    ast.Not: "!",
}

BOOL_OPS: dict[type[ast.boolop], str] = {
    ast.And: "&&",
    ast.Or: "||",
}

COMP_OPS: dict[type[ast.cmpop], str] = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
}

DOC_TEMPLATE: str = "/-- {doc} -/"
