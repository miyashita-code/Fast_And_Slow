import os


from dotenv import load_dotenv

from langchain.tools.base import BaseTool



class UpdataInstructions(BaseTool):
    """Tool that updates instructions."""

    name = "updata_instructions"
    description = (
        "Updata instructions for client agent (not directly to user) with the text. and switch client agent's talking stlye instruction mode or lend to a Ear. To make the conversion with dementia's person better."
        "Input shold be a string instruction_text to updata instructions and bool of isLendingEar: if true , client agent use the prompt to ask more, else better telling mode."
        "instruction is used to decide to what to do next or hot to explain the next step by interface agent who really support dementia user to empower."
        "instruction_textの出力は日本語でなくてなならない。そして何がどうであるのでどうしたいかを明確にすること。現状のコンテキストと今後の想定も含めるとわかりやすい。"
        "isLendingEarの出力は'true' or 'false'でなくてはならない。"
        "instruction_text and isLendingEar must be updated frequently to make the conversation better on realtime."
        "特に認知症の当事者の感じている世界を想像して寄り添うことが大切である。誇りをもって、尊敬の念をもって、寄り添うことが大切である。でたらめな話題を振るべきだはない。"
    )



    def _run(self, instruction_text, isLendingEar) -> str:
        return f"Instructions for the conversation is updated with {instruction_text}, isLendingEar is {isLendingEar}"


    async def _arun(self, instruction_text) -> str:
        return self._run(instruction_text)
    
    @classmethod
    def get_tool_name(cls) -> str:
        return "updata_instructions"
