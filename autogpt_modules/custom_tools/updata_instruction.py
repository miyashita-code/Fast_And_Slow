import os


from dotenv import load_dotenv

from langchain.tools.base import BaseTool



class UpdataInstructions(BaseTool):
    """Tool that updates instructions."""

    name = "updata_instructions"
    description = (
        "Updata instructions with the text. To make the conversion better."
        "Input shold be a string instruction_text to updata instructions."
        "instruction is used to decide to what to do next or hot to explain the next step by interface agent who really support dementia user to empower."
        "出力は日本語でなくてなならない。そして何がどうであるのでどうしたいかを明確にすること。"
        "instruction_must be updated frequently to make the conversation better on realtime."
        "特に認知症の当事者の感じている世界を想像して寄り添うことが大切である。"
    )


    def _run(self, instruction_text) -> str:
        return f"Instructions for the conversation is updated with {instruction_text}"


    async def _arun(self, instruction_text) -> str:
        return self._run(instruction_text)
    
    @classmethod
    def get_tool_name(cls) -> str:
        return "updata_instructions"
