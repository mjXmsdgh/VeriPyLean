"""
handlers パッケージ:
ASTノードごとの変換ロジックを統合します。
"""
from .utils import extract_doc_and_body, format_args, get_block_lines
from .expressions import (
    handle_op, handle_list_comp, handle_call, 
    BUILTIN_CALL_HANDLERS, METHOD_CALL_HANDLERS
)
from .statements import handle_if
from .definitions import handle_function_def, handle_class_def