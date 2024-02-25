import os
#import websocket

from dotenv import load_dotenv

from langchain.tools.base import BaseTool



class UpdataInstructions(BaseTool):
    """Tool that updates instructions."""

    name = "updata_instructions"
    description = (
        "Updata instructions with the text. To make the conversion better."
        "Input shold be a string instruction_text to updata instructions and must be in 日本語."
    )





    def _run(self, instruction_text : str) -> str:
        pass
        
        return f"Instructions for the conversation is updated with {instruction_text}"


    async def _arun(self, instruction_text) -> str:
        return self._run(instruction_text)
