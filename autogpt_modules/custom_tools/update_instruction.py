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

        # load env as instead of init
        load_dotenv()
        is_dev_env_with_instruction_file = True if os.getenv("IS_DEV_ENV_WITH_INSTRUCTION_FILE") == "True" else False

        if is_dev_env_with_instruction_file:
            instruction_file_path = os.getenv("INSTRUCTION_FILE_PATH")
        
        websocket_url = os.getenv("WEBSOCKET_URL")

        # for dev mode, update instruction file
        if is_dev_env_with_instruction_file:
            with open(instruction_file_path, mode="w") as f:
                f.write(instruction_text)

        # for prod mode, update instruction via websocket
        else:
            #ws = websocket.create_connection(websocket_url)
            #ws.send(instruction_text)
            #ws.close()
            pass
        
        return f"Instructions for the conversation is updated with {instruction_text}"


    async def _arun(self, instruction_text) -> str:
        return self._run(instruction_text)
