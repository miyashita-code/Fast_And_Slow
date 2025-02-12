from dataclasses import dataclass
from typing import List, Optional, Dict

@dataclass
class ContextInfo:
    """コンテキスト情報を管理するクラス"""
    global_context: str = ""
    local_context: List[str] = None

    def __init__(self, global_context: str = "", local_context: Optional[List[str]] = None):
        self.global_context = global_context
        self.local_context = local_context if local_context is not None else []

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> 'ContextInfo':
        if not data:
            return cls()
        local_ctx = data.get('local_context', [])
        if isinstance(local_ctx, str):
            local_ctx = [local_ctx]
        elif not isinstance(local_ctx, list):
            local_ctx = []
        return cls(
            global_context=data.get('global_context', ''),
            local_context=local_ctx
        )

    def to_dict(self) -> Dict:
        return {
            "global_context": self.global_context,
            "local_context": self.local_context
        }
