from pydantic import BaseModel
from typing import List, Optional
from langchain.schema import HumanMessage, AIMessage

from pydantic import BaseModel
from typing import List, Optional

class TextContent(BaseModel):
    text: str

class UserMessage(BaseModel):
    name: Optional[str] = None
    contents: List[TextContent]

    class Config:
        arbitrary_types_allowed = True

class AiMessage(BaseModel):
    text: str
    toolExecutionRequests: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

def convert_to_langchain_message(message):
    if isinstance(message, UserMessage):
        message_content = message.contents[0].text if message.contents else ""
        return HumanMessage(content=message_content), message_content
    elif isinstance(message, AiMessage):
        message_content = message.text
        return AIMessage(content=message_content), message_content
    else:
        print(f"Invalid message type: {type(message)}")
        raise ValueError("Invalid message type")
    