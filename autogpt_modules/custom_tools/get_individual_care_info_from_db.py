from langchain.tools.base import BaseTool

class GetIndividualCareInfoFromDB(BaseTool):
    """Tool that pander and analize current dialog state to conduct better instruction."""

    name = "get_individual_care_inform_db"

    description = (
        "Tool that get individual care info from db to make instruction for dementia user better."
        "Input shold be a string about_what to search from db."
        "example : デイの準備"
        "参照されるすべての情報はここから取得される。"
        "それは、ユーザーの個別のケア情報を取得し、その情報をもとに、ユーザーに最適なケアを提供するために使用される。"
        "ユーザーにインストラクションを提供するためには、ユーザーの個別のケア情報を取得する必要がある。"
    )

    # this function must aceess to the memory, so it is not implemented here. but in the auto_gpt.py itself

    def _run(self, about_what) -> str:

        ans = """
        1. 髭剃り : 剃刀ではなく、赤色の電動シェイバーがあるのでそれを使って!
        2. 予定(月, 水, 金) : デイサービスもえん家(ち)に行く予定があります. 荷物を準備して, 着替えをしませんか?. 髭剃りも忘れないように!. 9時ごろに職員さんが, 車でお迎えに来ます.
        3. 予定(土) : お昼(13:00)から, 将棋の宮下君が来るので, 身支度を済まませんか?.

        月曜日の朝、デーサービスの迎えが9:00に来るので、その前に外出の準備。
        基本的には、身だしなみの準備をお迎えの予定時間前に終わらせることが目的。
        なお、8:30ゴロに朝食をたべるので、そのあとのことである。そこは柔軟に。
        身だしなみの準備は顔回りと服装の2つがある。顔回りは、顔を洗う、歯磨き、ひげをそるの3つのプロセスで基本的に構築される。
        ひげをそるときは、剃刀負けするといけないので、赤の電動シェイバーを使ってもらう。なお、電動シェイバーは、洗面台の上にある。
        服装については、外がすごく寒いときはグレーのコート、少し寒いときは茶色のコートを使うとよい。迎えが9:00に来るので、8:50ぐらいに着替えを済ませるとよい。
        """
        return f"Individual care info is got from db with {about_what} and current answer is {ans}."



    async def _arun(self, goal_of_dialog_analyze : str, dialog_data : str) -> str:
        return self._run(goal_of_dialog_analyze, dialog_data)

    @classmethod
    def get_tool_name(cls) -> str:
        return "pander_dialog_state"

