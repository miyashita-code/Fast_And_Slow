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
            ws = websocket.create_connection(websocket_url)
            ws.send(instruction_text)
            ws.close()
        
        return f"Instructions for the conversation is updated with {instruction_text}"


    async def _arun(self, instruction_text) -> str:
        return self._run(instruction_text)
    
    @classmethod
    def get_tool_name(cls) -> str:
        return "updata_instructions"
