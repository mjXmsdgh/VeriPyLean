import ast
from .. import types
from . import constants
from . import handlers
from .context import CodeBuilder

class LeanTranslator(ast.NodeVisitor):
    """Python ASTを走査し、再帰的にLean 4の構文へと変換するメインビジター"""
    def __init__(self, context):
        self.context = context

    def visit_Module(self, node):
        """ルートノード: 全てのステートメントを変換して結合する"""
        return "\n\n".join(filter(None, [self.visit(stmt) for stmt in node.body]))

    def generic_visit(self, node):
        """未知のノードに対するデフォルトのフォールバック"""
        return self._unsupported(node)

    def _v(self, node):
        """再帰的な変換のヘルパー"""
        if node is None: return ""
        return self.visit(node)

    def _unsupported(self, node, detail=None):
        """サポート外の機能に遭遇した際の共通処理"""
        node_type = type(node).__name__
        msg = f"Python feature '{node_type}' is not supported yet"
        if detail: msg += f" ({detail})"
        self.context.add_warning(node, msg)
        return f"/- {msg} -/ sorry"

    def _extract_doc_and_body(self, node):
        """ノードからdocstringを除去した本体ステートメントを返す"""
        doc = ast.get_docstring(node)
        stmts = node.body
        # docstringが最初の式として存在する場合、bodyから除外
        if doc and stmts and isinstance(stmts[0], ast.Expr):
            stmts = stmts[1:]
        return doc, stmts

    def _format_args(self, args_node):
        """関数引数を (name : Type) の形式で結合する"""
        return " ".join([f"({a.arg} : {types.translate_type(a.annotation)})" for a in args_node.args])

    def _wrap(self, node, trigger_types=(ast.Call, ast.IfExp, ast.BinOp, ast.Compare)):
        """必要に応じて式を括弧で囲む"""
        res = self._v(node)
        if isinstance(node, trigger_types):
            return f"({res})"
        return res

    def visit_FunctionDef(self, node):
        doc, stmts = self._extract_doc_and_body(node)
        args = self._format_args(node.args)
        is_thm = node.name.startswith(("verify_", "theorem_"))
        meta = self.context.functions.get(node.name, {})
        return self._build_function_or_theorem(node, doc, stmts, args, is_thm, meta)

    def visit_ClassDef(self, node):
        """クラス定義をEnumまたはStructure(Dataclass)として変換する"""
        kind = self.context.classes.get(node.name)
        if kind == "enum":
            return self._translate_enum(node)
        if kind == "structure":
            return self._translate_structure(node)
        return self._unsupported(node, "Only Enums and @dataclass are supported")

    def visit_Assign(self, node): return f"let {self._v(node.targets[0])} := {self._v(node.value)};"
    def visit_Constant(self, node): return f'"{node.value}"' if isinstance(node.value, str) else str(node.value)
    def visit_Name(self, node): return node.id
    def visit_Attribute(self, node): return f"{self._v(node.value)}.{node.attr}"
    def visit_Return(self, node): return self._v(node.value)
    def visit_Assert(self, node): return f"have : {self._v(node.test)} := by sorry;"
    def visit_Expr(self, node): return self._v(node.value)
    def visit_BinOp(self, node):
        l, r = self._v(node.left), self._v(node.right)
        if isinstance(node.op, ast.Div): return f"(py_div ({l}) ({r}))"
        op = constants.BIN_OPS.get(type(node.op))
        return f"({l} {op} {r})" if op else self._unsupported(node.op)

    def _translate_block(self, builder, stmts, is_theorem=False):
        """複数のステートメントをLeanのブロックとして変換し、builderに追加する共通ロジック"""
        if not stmts:
            builder.add("()" if not is_theorem else "True")
            return

        for i, stmt in enumerate(stmts):
            translated = self._v(stmt)
            # 各ステートメントの出力を1行ずつbuilderに渡す
            for line in translated.splitlines():
                builder.add(line)
            
            # 最後のステートメントが代入や表明(let/have)で終わる場合、
            # Leanの式を完結させるためのダミー値を追加する
            if i == len(stmts) - 1:
                if isinstance(stmt, (ast.Assign, ast.Assert)):
                    builder.add("()" if not is_theorem else "True")

    def visit_IfExp(self, node):
        return f"if {self._v(node.test)} then {self._v(node.body)} else {self._v(node.orelse)}"

    def visit_If(self, node):
        builder = CodeBuilder()
        with builder.block(f"if {self._v(node.test)} then"):
            self._translate_block(builder, node.body)
        if node.orelse:
            with builder.block("else"):
                self._translate_block(builder, node.orelse)
        else:
            builder.add("else ()")
        return builder.build()

    def visit_BoolOp(self, node):
        op = constants.BOOL_OPS.get(type(node.op), "??")
        return f"({(f' {op} ').join([self._v(v) for v in node.values])})"
    def visit_UnaryOp(self, node):
        op = constants.UNARY_OPS.get(type(node.op))
        return f"({op}{self._v(node.operand)})" if op else self._unsupported(node.op)
    def visit_Compare(self, node):
        parts, curr = [], self._v(node.left)
        for op, comp in zip(node.ops, node.comparators):
            next_v = self._v(comp)
            parts.append(f"({curr} {constants.COMP_OPS.get(type(op), '?')} {next_v})")
            curr = next_v
        return parts[0] if len(parts) == 1 else f"({' && '.join(parts)})"
    def visit_List(self, node): return f"[{', '.join([self._v(e) for e in node.elts])}]"
    def visit_Tuple(self, node): return f"({', '.join([self._v(e) for e in node.elts])})"

    def visit_Call(self, node):
        fn = self._v(node.func)
        h = handlers.BUILTIN_CALL_HANDLERS.get(fn) or (isinstance(node.func, ast.Attribute) and handlers.METHOD_CALL_HANDLERS.get(node.func.attr))
        if h:
            res = h(node, self)
            if res: return res
        args = [self._wrap(a, trigger_types=(ast.IfExp, ast.BinOp)) for a in node.args]
        return fn if not args else f"{fn} {' '.join(args)}"

    def visit_ListComp(self, node):
        return self._translate_list_comp_recursive(node.generators, node.elt)

    def visit_For(self, node): return "-- [PyLean] Error: for loops are not supported. Use list comprehensions or recursion."
    def visit_Pass(self, node): return "()"

    def _translate_enum(self, node):
        builder = CodeBuilder()
        with builder.block(constants.IND_HEADER.format(name=node.name)):
            for s in node.body:
                if isinstance(s, ast.Assign):
                    for t in s.targets:
                        if isinstance(t, ast.Name):
                            builder.add(f"| {t.id}")
        builder.add(constants.DERIVING_FOOTER)
        return builder.build()

    def _translate_structure(self, node):
        builder = CodeBuilder()
        with builder.block(constants.STRUCT_HEADER.format(name=node.name)):
            for s in node.body:
                if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name):
                    builder.add(f"{s.target.id} : {types.translate_type(s.annotation)}")
        builder.add(constants.DERIVING_FOOTER)
        return builder.build()

    def _translate_list_comp_recursive(self, generators, elt):
        if not generators: return self._v(elt)
        gen, *rest = generators
        inner = self._translate_list_comp_recursive(rest, elt)
        target, iterable = self._v(gen.target), self._v(gen.iter)
        if not gen.ifs:
            method = "map" if not rest else "flatMap"
            return f"({iterable}).{method} (fun {target} => {inner})"
        cond = " && ".join(f"({self._v(c)})" for c in gen.ifs)
        if not rest:
            return f"({iterable}).filterMap (fun {target} => if {cond} then some ({inner}) else none)"
        return f"({iterable}).filter (fun {target} => {cond}).flatMap (fun {target} => {inner})"

    def _build_function_or_theorem(self, node, doc, stmts, args, is_thm, meta):
        builder = CodeBuilder()
        if doc:
            builder.add(constants.DOC_TEMPLATE.format(doc=doc))

        is_ret = is_thm and isinstance(stmts[-1], ast.Return)
        prop = self._v(stmts[-1].value) if is_ret else "True"
        ret_type = types.translate_type(node.returns)
        
        if is_thm:
            header = constants.THM_HEADER.format(
                name=node.name, args=args, prop=prop
            )
        else:
            header = constants.DEF_HEADER.format(
                name=node.name, args=args, ret_type=ret_type
            )

        body_stmts = stmts[:-1] if is_ret else stmts

        with builder.block(header):
            if not body_stmts and not is_thm:
                builder.add("sorry")
            elif is_thm:
                self._translate_block(builder, body_stmts, is_theorem=True)
                builder.add(constants.THM_PROOF)
            else:
                self._translate_block(builder, body_stmts, is_theorem=False)

        hint = meta.get("hint")
        if meta.get("is_recursive"):
            if hint:
                builder.add(constants.TERMINATION_BY.format(hint=hint))
            else:
                return constants.REC_WARN.format(code=builder.build())
        
        return builder.build()