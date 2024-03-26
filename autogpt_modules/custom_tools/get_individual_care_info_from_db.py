from langchain.tools.base import BaseTool

class GetIndividualCareInfoFromDB(BaseTool):
    """Tool that pander and analize current dialog state to conduct better instruction."""

    name = "get_individual_care_inform_db"

    description = (
        "Tool that get individual care info from db to make instruction for dementia user better."
        "Input shold be a string about_what to search from db."
        "example : bath prepare"
    )

    # this function must aceess to the memory, so it is not implemented here. but in the auto_gpt.py itself

    def _run(self, goal_of_dialog_analyze : str, dialog_data : str) -> str:

        ans = """
        1. 髭剃り : 剃刀ではなく、赤色の電動シェイバーがあるのでそれを使って!
        2. 予定(月, 水, 金) : デイサービスもえん家(ち)に行く予定があります. 荷物を準備して, 着替えをしませんか?. 髭剃りも忘れないように!. 9時ごろに職員さんが, 車でお迎えに来ます.
        3. 予定(土) : お昼(13:00)から, 将棋の宮下君が来るので, 身支度を済まませんか?.
        """
        return ans



    async def _arun(self, goal_of_dialog_analyze : str, dialog_data : str) -> str:
        return self._run(goal_of_dialog_analyze, dialog_data)

    @classmethod
    def get_tool_name(cls) -> str:
        return "pander_dialog_state"

