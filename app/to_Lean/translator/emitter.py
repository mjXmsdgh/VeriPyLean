from .context import CodeBuilder
from . import constants

class LeanEmitter:
    """Lean 4の具体的な構文文字列を生成する責務を持つクラス"""
    def __init__(self, context):
        self.context = context

    def format_doc(self, doc):
        return constants.DOC_TEMPLATE.format(doc=doc) if doc else ""

    def format_let(self, target, value):
        return f"let {target} := {value};"

    def format_have(self, prop):
        return f"have : {prop} := by sorry;"

    def format_if_expr(self, test, body, orelse):
        return f"if {test} then {body} else {orelse}"

    def format_if_stmt(self, test, then_lines, else_lines=None):
        builder = CodeBuilder()
        with builder.block(f"if {test} then"):
            for line in then_lines:
                for l in str(line).splitlines():
                    builder.add(l)
        if else_lines:
            with builder.block("else"):
                for line in else_lines:
                    for l in str(line).splitlines():
                        builder.add(l)
        else:
            builder.add("else ()")
        return builder.build()

    def format_inductive(self, name, variants):
        builder = CodeBuilder()
        header = constants.IND_HEADER.format(name=name)
        with builder.block(header):
            for v in variants:
                builder.add(f"| {v}")
        builder.add(constants.DERIVING_FOOTER)
        return builder.build()

    def format_structure(self, name, fields):
        builder = CodeBuilder()
        header = constants.STRUCT_HEADER.format(name=name)
        with builder.block(header):
            for f_name, f_type in fields:
                builder.add(f"{f_name} : {f_type}")
        builder.add(constants.DERIVING_FOOTER)
        return builder.build()

    def format_function(self, name, args, ret_type, body_lines, doc=None, termination_hint=None, is_recursive=False):
        builder = CodeBuilder()
        if doc:
            builder.add(self.format_doc(doc))
        
        header = constants.DEF_HEADER.format(name=name, args=args, ret_type=ret_type)
        with builder.block(header):
            if not body_lines:
                builder.add("sorry")
            else:
                for line in body_lines:
                    for l in str(line).splitlines():
                        builder.add(l)
        
        if is_recursive:
            if termination_hint:
                builder.add(constants.TERMINATION_BY.format(hint=termination_hint))
            else:
                # 停止性ヒントがない再帰関数には警告を付与
                return constants.REC_WARN.format(code=builder.build())
        
        return builder.build()

    def format_theorem(self, name, args, prop, body_lines, doc=None):
        builder = CodeBuilder()
        if doc:
            builder.add(self.format_doc(doc))
        
        header = constants.THM_HEADER.format(name=name, args=args, prop=prop)
        with builder.block(header):
            if not body_lines:
                builder.add("skip")
            else:
                for line in body_lines:
                    for l in str(line).splitlines():
                        builder.add(l)
            builder.add(constants.THM_PROOF)
        return builder.build()
