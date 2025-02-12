from enum import Enum

class SocketEventType(Enum):
    NEXT_STATE_INFO = "next_state_info"
    INSTRUCTION = "instruction"
    TELLUSER = "telluser"
    CALL_TO_ACTION = "call_to_action"
    ANNOUNCE = "announce" 