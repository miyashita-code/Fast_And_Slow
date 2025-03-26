# メインの会話コントローラー
from typing import NamedTuple, Optional


class State(NamedTuple):
    description: str
    name: str
    time: int
    next_state: str = ""
    detail_name: Optional[str] = None
    title: str = ""
    call_to_action: Optional[str] = None
    detail_instruction: Optional[str] = None
