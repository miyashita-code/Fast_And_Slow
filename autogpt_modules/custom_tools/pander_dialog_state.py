from langchain.tools.base import BaseTool

class PanderDialogState(BaseTool):
    """Tool that pander and analize current dialog state to conduct better instruction."""

    name = "pander_dialog_state"
    description = (
        "Tool that pander and analyze already provided dialog state to conduct better instruction at this ponit."
        "Input shold be a string goal_of_dialog_analyze to pander and dive into that and a string dialog_data that is buffer so please set (略)."
        "example : goal_of_dialog_analyze = 'ユーザーの置かれている状態と心理状態を明確にする。', dialog_data = '(略)'"
    )

    # this function must aceess to the memory, so it is not implemented here. but in the auto_gpt.py itself

    def _run(self, goal_of_dialog_analyze : str, dialog_data : str) -> str:
        return f"Dialog state is analyzed with {goal_of_dialog_analyze} and {dialog_data}."


    async def _arun(self, goal_of_dialog_analyze : str, dialog_data : str) -> str:
        return self._run(goal_of_dialog_analyze, dialog_data)

    @classmethod
    def get_tool_name(cls) -> str:
        return "pander_dialog_state"

