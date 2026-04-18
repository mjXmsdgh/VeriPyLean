import ast

def _handle_date_call(node, visitor):
    """date(y, m, d) を Date 構造体リテラルに変換する"""
    if len(node.args) == 3:
        a = [visitor._v(arg) for arg in node.args]
        return f"({{ year := {a[0]}, month := {a[1]}, day := {a[2]} }} : Date)"
    return None

HANDLERS = {
    "date": _handle_date_call,
    "datetime.date": _handle_date_call,
}