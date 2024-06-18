from langchain.tools.base import BaseTool
import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
)

class PanderDialogState(BaseTool):
    """Tool that pander and analize current dialog state to conduct better instruction."""

    name = "pander_dialog_state"
    description = (
        "Tool that pander and analyze already provided dialog state to conduct better instruction at this ponit."
        " dialog_data, autogpt_data, current_state_infos are used to analyze the dialog state BUT THESE ARE GIVEN OTHER TOOL, SO YOU DON'T NEED TO CARE ABOUT IT."
        "Input shold be a string goal_of_dialog_analyze to pander and dive into that."
        "example : goal_of_dialog_analyze = 'ユーザーの置かれている状態と心理状態を明確にする。', '現状の把握と支援の計画のフローを作成する。'"
        "***注意***However, it takes a little time, and heavy use will cause delays in assisting the user, so use should be limited to important situations only.***注意***"
    )

    # this function must aceess to the memory, so it is not implemented here. but in the auto_gpt.py itself

    def _run(self, goal_of_dialog_analyze, dialog_data, autogpt_data, current_state_infos) -> str:
        ans = self.call_LLM(self, goal_of_dialog_analyze, dialog_data, autogpt_data, current_state_infos)

        return f"Dialog state is analyzed with {goal_of_dialog_analyze} and current answer is {ans}."


    async def _arun(self, goal_of_dialog_analyze, dialog_data, autogpt_data, current_state_infos) -> str:
        return self._run(self, goal_of_dialog_analyze, dialog_data, autogpt_data, current_state_infos)

    def call_LLM(self, goal_of_dialog_analyze, dialog_data, autogpt_data, current_state_infos) -> str:
        message = client.messages.create(
            model="claude-3-sonnet-20240229", # モデル名
            temperature=0.0, # 0.0-1.0
            system=f"Here we have a group of three care professionals: one is a specialist in dementia care, one is a helper in independent assistance, and one is a care manager. Please analyze and discuss the following information on care and create an answer with GOAL's current status. Your answer should be long enough to include thought flow along the way. Note that the Independence Support Client Agent is interacting with the user with dementia here. The autogpt is a mechanism to control it well.\n[goal_of_dialog_analyze (この議論の目標)] {goal_of_dialog_analyze},\n [dialog_data(dementia userとclient agentの対話履歴)] {dialog_data}, \n[autogpt_data (sutogptの思考履歴)] {autogpt_data}, \n[current_state_infos (現状の細かな状態)] {current_state_infos}\n\nlast_instruction is the content of the instruction from autogpt to the client agent. last_isLendingEar indicates whether the client aget is currently in a listening mode to elicit information or is prompting to improve IADL. Also, shownMessageOnDisplay is the content of the output directly on the screen for the user's understanding. It is also useful to consider what to do with these as a landing point for discussion.", # 必要ならシステムプロンプトを設定
            messages=[
                {
                    "role": "user",
                    "content": "議論を始めてください！"
                }
            ]
        )

        print(message.content[0].text)

    @classmethod
    def get_tool_name(cls) -> str:
        return "pander_dialog_state"


