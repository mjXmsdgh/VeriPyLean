from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any, Callable

from . import accounting_handlers, datetime_handlers, math_handlers

if TYPE_CHECKING:
    from ...core import LeanTranslator

BUILTIN_CALL_HANDLERS: dict[str, Callable[[ast.Call, LeanTranslator], str | None]] = {
    **math_handlers.HANDLERS,
    **accounting_handlers.HANDLERS,
    **datetime_handlers.HANDLERS,
}

METHOD_CALL_HANDLERS: dict[str, Callable[[ast.Call, LeanTranslator], str | None]] = {
    **accounting_handlers.METHOD_HANDLERS,
}

def handle_call(node: ast.Call, v: LeanTranslator) -> str:
    """関数呼び出しの変換をハンドリングする（組み込みハンドラを含む）"""
    fn: str = v._v(node.func)
    h: Callable[[ast.Call, LeanTranslator], str | None] | None = BUILTIN_CALL_HANDLERS.get(fn) or (
        METHOD_CALL_HANDLERS.get(node.func.attr) if isinstance(node.func, ast.Attribute) else None
    )
    if h:
        res = h(node, v)
        if res: return res
    args: list[str] = [v._wrap(a, trigger_types=(ast.IfExp, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.Call)) for a in node.args]
    
    # 呼び出し対象関数のメタデータをチェックして事前条件証明を追加
    target_meta: dict[str, Any] = getattr(v.context, 'functions', {}).get(fn, {})
    target_preconds: list[ast.AST] = target_meta.get("preconditions", [])
    if target_preconds:
        curr_fn: str | None = getattr(v, 'current_function', None)
        curr_preconds: list[ast.AST] = []
        if curr_fn:
            curr_meta: dict[str, Any] = getattr(v.context, 'functions', {}).get(curr_fn, {})
            curr_preconds = curr_meta.get("preconditions", [])
            target_name: str | None
            if curr_fn.startswith("verify_"):
                target_name = curr_fn[len("verify_"):]
            elif curr_fn.startswith("theorem_"):
                target_name = curr_fn[len("theorem_"):]
            else:
                target_name = None
            if target_name:
                target_meta_curr: dict[str, Any] = getattr(v.context, 'functions', {}).get(target_name, {})
                curr_preconds = target_meta_curr.get("preconditions", [])
        
        curr_precond_strs: list[str] = [v._v(cond) for cond in curr_preconds]
        for t_cond in target_preconds:
            t_cond_str = v._v(t_cond)
            try:
                idx = curr_precond_strs.index(t_cond_str)
                args.append(f"h_precond_{idx}")
            except ValueError:
                args.append("(by sorry)")

    return fn if not args else f"{fn} {' '.join(args)}"