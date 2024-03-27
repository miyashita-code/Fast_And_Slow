import re
from langchain.schema import HumanMessage, AIMessage

def parse_to_langchain_message_str(raw_message : str):
    user_message_pattern = r'UserMessage\s*\{\s*name\s*=\s*(\w+|\w+)?\s*contents\s*=\s*\[TextContent\s*\{\s*text\s*=\s*"(.+?)"\s*}\]\s*}'
    ai_message_pattern = r'AiMessage\s*\{\s*text\s*=\s*"(.+?)"\s*toolExecutionRequests\s*=\s*(\w+|\w+)?\s*}'

    user_message_match = re.search(user_message_pattern, raw_message)
    ai_message_match = re.search(ai_message_pattern, raw_message)

    if user_message_match:
        message_content = user_message_match.group(2)
        return "user:" + message_content
    elif ai_message_match:
        message_content = ai_message_match.group(1)
        return "assistant:" + message_content
    else:
        raise ValueError("Invalid message format")
