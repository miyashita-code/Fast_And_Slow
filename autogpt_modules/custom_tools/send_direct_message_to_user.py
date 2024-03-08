import os


from dotenv import load_dotenv

from langchain.tools.base import BaseTool



class SendDirectMessageToUser(BaseTool):
    """Tool that updates direct instructions on user's screen"""

    name = "send_direct_message_to_user"
    description = (
        "Updata instruction message on user's screen directry with Generateing text to support user comprehension visually and display (title),"
        " Detailed content for client agents to assist users with dementia in interactive conversations about it (detail)."
        "***注意***注意***注意***出力は日本語でなくてなならない。そして何がどうであるのでどうしたいかを明確にすること。***注意***注意***注意***"
        "Input shold be a string instruction_title and string instruction_detail"
        "instruction_title is actually displayed on the user's screen, so be careful not to stigmatize the user. "
        "This text can be used to present a summary of a conversation to supplement the user's understanding and short-term memory, "
        "or to present key points for actions and tasks in an easy-to-understand order of execution. Alternatively, it can push the user by presenting key points for action or tasks in a clear and understandable order of execution."
        "instruction is used to decide what to do next or how to explain the next step by interface agent who really support dementia user to empower."
        "instruction_title must be updated relatively frequently to make the conversation better on realtime. but, It is easier for users to understand if the title is somewhat consistent."
        "***注意***注意***注意***出力は日本語でなくてなならない。そして何がどうであるのでどうしたいかを明確にすること。***注意***注意***注意***"
        "特に認知症の当事者の感じている世界を想像して寄り添うことが大切である。"
    )



    def _run(self, instruction_title, instruction_detail) -> str:
        return f"Instructions for the conversation is updated with {instruction_title} and {instruction_detail}"


    async def _arun(self, instruction_text) -> str:
        return self._run(instruction_text)
    
    @classmethod
    def get_tool_name(cls) -> str:
        return "send_direct_message_to_user"
