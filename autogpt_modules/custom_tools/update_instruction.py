import os
import websocket

from dotenv import load_dotenv

from langchain.tools.base import BaseTool



class update_instructions(BaseTool):
    """Tool that updates instructions."""

    name = "update_instructions"
    description = (
        "Update instructions with the text. To make the conversion better."
        "Input shold be a string instruction_text to update instructions."
    )

    def __init__(self):
        load_dotenv()
        self.is_dev_env_with_instruction_file = True if os.getenv("IS_DEV_ENV_WITH_INSTRUCTION_FILE") == "True" else False

        if self.is_dev_env_with_instruction_file:
            self.instruction_file_path = os.getenv("INSTRUCTION_FILE_PATH")
        
        self.websocket_url = os.getenv("WEBSOCKET_URL")


    def _run(self, instruction_text : str) -> str:

        # for dev mode, update instruction file
        if self.is_dev_env_with_instruction_file:
            with open(self.instruction_file_path, mode="w") as f:
                f.write(instruction_text)

        # for prod mode, update instruction via websocket
        else:
            ws = websocket.create_connection(self.websocket_url)
            ws.send(instruction_text)
            ws.close()
        
        return f"Instructions for the conversation is updated with {instruction_text}"


    async def _arun(self, instruction_text) -> str:
        return self._run(instruction_text)
