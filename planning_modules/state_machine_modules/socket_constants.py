from enum import Enum

class SocketEventType(Enum):
    NEXT_STATE_INFO = "next_state_info"
    INSTRUCTION = "instruction"
    TELLUSER = "telluser"
    CALL_TO_ACTION = "call_to_action"
    ANNOUNCE = "announce"
    INSTRUCTION_CANDIDATES = "instruction_candidates"  # 候補一覧の送信
    START_INSTRUCTION = "start_instruction"  # 選択された候補の開始 