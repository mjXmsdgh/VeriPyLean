from .utils import get_block_lines

def handle_if(node, v):
    """If文の変換をハンドリングする"""
    then_lines = get_block_lines(v, node.body)
    else_lines = get_block_lines(v, node.orelse) if node.orelse else None
    return v.emitter.format_if_stmt(v._v(node.test), then_lines, else_lines)