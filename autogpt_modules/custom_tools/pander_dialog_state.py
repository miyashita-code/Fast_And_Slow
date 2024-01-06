from langchain.tools.base import BaseTool

class Pander_Dialog_State(BaseTool):
    """Tool that pander and analize current dialog state to conduct better instruction."""

    name = "pander_dialog_state"
    description = (
        "Tool that pander and analyze current dialog state to conduct better instruction."
        "Input shold be a string goal_of_dialog_analyze to pander and dive into that."
    )

    # this function must aceess to the memory, so it is not implemented here. but in the auto_gpt.py itself

    def _run(self, goal_of_dialog_analyze : str) -> str:
        pass


    async def _arun(self, goal_of_dialog_analyze : str) -> str:
        return self._run(goal_of_dialog_analyze)

    @classmethod
    def get_tool_name(cls) -> str:
        return cls.name

