from typing import Callable, List, NamedTuple
import asyncio
from pydantic import BaseModel
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_fireworks import ChatFireworks
from langchain_core.runnables import RunnableSequence
from dotenv import load_dotenv
import threading

# 環境変数の読み込み
load_dotenv()

# LLMの出力モデル
class CheckIsExplainedOutput(BaseModel):
    thought: str
    is_explained: bool

class CheckIsFinishedOutput(BaseModel):
    thought: str
    is_finished: bool

# プロンプトテンプレート
check_is_explained_prompt = """
Your Task:
You need to check whether the user's responses sufficiently explain the given detail within the context of the conversation flow. If the responses explain the detail clearly, respond with 'True'. Otherwise, respond with 'False'. Additionally, include a thought process explaining why you reached that conclusion.

Here is the overall conversation flow (for context):
{global_responses}

Here are the user's specific responses to be checked:
{responses}

Here is the specific detail that needs to be explained:
{detail}

Follow these output format instructions (100%, only json output):
{format_instructions}

caution:
even if there are no user responses to check, json以外で答えるな！一文字も追加するな！
"""

check_is_finished_prompt = """
Your Task:
You need to check whether the user's responses sufficiently indicate that the current topic is finished and ready to move to the next topic. If the user's responses sufficiently address the topic, respond with 'True'. Otherwise, respond with 'False'. Additionally, include a thought process explaining why you reached that conclusion.

Here is the overall conversation flow (for context):
{global_responses}

Here are the user's specific responses to be checked:
{responses}

Here is the current topic (detail) that needs to be addressed:
{detail}

Here is the name of the next state or topic we plan to transition to:
{next_state_name}

Follow these output format instructions (100%, only json output):
{format_instructions}

caution:
even if there are no user responses to check, json以外で答えるな！一文字も追加するな！, 「次は？」とか言われたらすぐに次に行け！次の内容の話を始めてもすぐに次に行け！
"""

# 出力パーサー
output_parser_check_is_explained = JsonOutputParser(pydantic_object=CheckIsExplainedOutput)
output_parser_check_is_finished = JsonOutputParser(pydantic_object=CheckIsFinishedOutput)

# プロンプトテンプレート
prompt_template_check_is_explained = PromptTemplate.from_template(
    check_is_explained_prompt,
    partial_variables={
        "format_instructions": output_parser_check_is_explained.get_format_instructions()
    }
)

prompt_template_check_is_finished = PromptTemplate.from_template(
    check_is_finished_prompt,
    partial_variables={
        "format_instructions": output_parser_check_is_finished.get_format_instructions()
    }
)

# LLMモデル
fast_model = ChatFireworks(model="accounts/fireworks/models/llama-v3-70b-instruct", max_tokens=4096)

# 実行シーケンス
check_is_explained_chain = prompt_template_check_is_explained | fast_model | output_parser_check_is_explained
check_is_finished_chain = prompt_template_check_is_finished | fast_model | output_parser_check_is_finished

# メインの会話コントローラー
class State(NamedTuple):
    detail: str
    name: str
    time: int
    next_state: str = ""
    title: str = ""

class LinearConversationController:
    def __init__(self, llm_client, threshold: float = 0.7):
        self.states = self.get_init_state()
        self.current_state_index = 0
        self.llm_client = llm_client
        self.threshold = threshold
        self.is_on = False
        self.is_explained = False
        self.responses_buffer = []
        self.global_responses_buffer = []
        self.callback = None
        self.direct_prompting_func = None
        self.timer = None
        self.timeout_count = 0
        self.thread = None
        self.state_changed = False  # 状態変化を追跡するフラグを追加
        self.loop = None  # イベントループを初期化

    def set_callbacks(self, callback: Callable, direct_prompting_func: Callable):
        self.callback = callback
        self.direct_prompting_func = direct_prompting_func

    """
    def get_init_state(self) -> List[State]:
        return [
            State(detail="iphoneのmapの使い方を説明します。", name="iphoneのmapの使い方説明", time=0, next_state="iphoneのホーム画面を開く", title="iphoneのmapの使い方説明"),
            State(detail="まずはiphoneを手に取り, 電源を入れてホーム画面を開いてください。", name="iphoneのホーム画面を開く", time=0, next_state="マップ アプリを開く", title="iphoneのホーム画面を開く"),
            State(detail="まずは、mapのアプリの中に入りたいので、画面の右下の方にある「マップ アプリを開いてください」", name="マップ アプリを開く", time=1, next_state="マップで検索をタップ", title="画面右下のマップ アプリを開く"),
            State(detail="マップを開いたら、目的地を検索します。画面の下の方の虫眼鏡のアイコンの横に「マップで検索」と書いてあるところをタップか長押ししてください。キーボードが出てきます。", name="マップで検索をタップ", time=0, next_state="目的地を入力", title="「🔍マップで検索」をタップ"),
            State(detail="キーボードが出てきたら、キーボードで目的地の住所か名前を入力してください。入力後、入力欄の下に表示された候補の中から目的のものを見つけてタップしてください。", name="目的地を入力", time=1, next_state="経路ボタンをタップ", title="目的地をキーボードで入力"),
            State(detail="画面下部に青色のボタンで「経路」と書いてあるボタンがあります。このボタンをタップしてください。そうすれば出発地を選択の画面が出てきます。もしない場合は下に隠れているかもしれないです。", name="経路ボタンをタップ", time=0, next_state="現在地を選択", title="画面下部の青色の経路ボタンをタップ"),
            State(detail="出発地点の入力を求められたら、現在地を選択してください。そのあと、右上の青色の経路を選択します。", name="現在地を選択", time=0, next_state="出発", title="出発地に現在地を選択"),
            State(detail="あとは画面下部右下の出発をタップして、出発です！お気をつけて！", name="出発", time=0, next_state="終了", title="出発をタップしてお気をつけて！"),
        ]
    """

    def get_init_state(self) -> List[State]:

        return [
            State(
                detail="散歩に行きませんか？",
                name="着替えをする",
                time=0,
                next_state="上着を着る",
                title="散歩に行きませんか？ 着替えをする"
            ),
            State(
                detail="外に行く前に服装だけ整えたいですね。今日は外の気温が低いので、温かい上着を着るのがおすすめですよ。(5~10度前後みたいですよ)",
                name="上着を着る",
                time=0,
                next_state="トイレに行く",
                title="上着を着る"
            ),
            State(
                detail="靴下と上着の準備が済んだら、念のためトイレを済ませておくと安心ですね。",
                name="トイレに行く",
                time=0,
                next_state="靴箱に向かう",
                title="トイレに行く"
            ),
            State(
                detail="それでは、1階の靴箱に向かいましょう。",
                name="靴箱に向かう",
                time=0,
                next_state="不安を取り除く",
                title="靴箱に向かう"
            ),
            State(
                detail="スリッパのままでいいのか、靴はどこにあるのか不安になることがあるかもしれませんが、下に靴箱があるので大丈夫ですよ。",
                name="不安を取り除く",
                time=1,
                next_state="終了",
                title="不安を取り除く"
            ),
            State(
                detail="これで準備が完了しました。お気をつけていってらっしゃい！",
                name="終了",
                time=0,
                next_state="終了",
                title="お気をつけて！"
            ),
        ]   


    def set_mode(self, mode: bool):
        self.is_on = mode

    def get_mode(self):
        return self.is_on

    async def set_context(self, context: str):
        await self.__deal_user_response(context)

    async def __deal_user_response(self, response: str):
        self.global_responses_buffer.append(response)

        if self.current_state_index >= len(self.states):
            return

        if not self.is_on:
            return

        if "assistant" in response and not self.is_explained:
            print(f"global_responses_buffer: {self.global_responses_buffer}, responses_buffer: {self.responses_buffer}, detail: {self.states[self.current_state_index].detail}")
            thought, result = await self.check_is_explained(self.global_responses_buffer, self.responses_buffer, self.states[self.current_state_index].detail)
            print(f"Check is explained thought: {thought}")
            if result:
                self.is_explained = True
            else:
                await self.direct_prompting_func(
                    f"次の内容について可能な限り早い段階で伝えてください。ただし対話の文脈を壊さないように少し言い方を変えても構いません。内容: {self.states[self.current_state_index].detail}, また場合によっては次のステップに進んでもいいです。（次のステップの内容{self.states[min(self.current_state_index+1, len(self.states)-1)].detail}",
                    self.states[self.current_state_index].title  # タイトルを追加
                )
        elif "user" in response and self.is_explained:
            self.responses_buffer.append(response)
            print(f"global_responses_buffer: {self.global_responses_buffer}, responses_buffer: {self.responses_buffer}, detail: {self.states[self.current_state_index].detail}, next_state: {self.states[self.current_state_index].next_state}")
            thought, is_finished = await self.check_is_finished(self.global_responses_buffer, self.responses_buffer, self.states[self.current_state_index].detail, self.states[self.current_state_index].next_state)
            print(f"Check is finished thought: {thought}")
            if is_finished:
                self.responses_buffer = []
                await self.proceed_to_next_state()
                self.is_explained = False
            else:
                await self.direct_prompting_func(
                    f"次の内容について可能な限り早い段階で伝えてください。すでに伝えている場合は、ゆっくりと傾聴し積極的に反応を引き出したり追加で掘り下げて説明してください。内容: {self.states[self.current_state_index].detail}, また場合によっては次のステップに進んでもいいです。（次のステップの内容{self.states[min(self.current_state_index+1, len(self.states)-1)].detail}",
                    self.states[self.current_state_index].title  # タイトルを追加
                )

        if self.timer:
            self.timer.cancel()

        if self.current_state_index < len(self.states):
            current_state = self.states[self.current_state_index]
            if current_state.time > 0:
                self.timeout_count = 0
                await self.set_timer()

    async def proceed_to_next_state(self):
        self.current_state_index += 1
        self.state_changed = True  # 状態が変化したことを記録

        # フラグやバッファのリセット
        self.is_explained = False
        self.responses_buffer.clear()
        self.global_responses_buffer.clear()

        print(f"current_state_index: {self.current_state_index}, states: {self.states}")
        if self.current_state_index >= len(self.states):
            await self.end_conversation()
        else:
            await self.send_next_message()

    async def send_next_message(self):
        if self.current_state_index < len(self.states):
            current_state = self.states[self.current_state_index]
            # direct_prompting_func に title を追加で渡すように修正
            await self.direct_prompting_func(
                f"Planing Systemから要請です。次の内容について可能な限り早い段階で伝えてください。なお、内容が不自然な場合は文脈が壊れないように少し言い方を変えても構いません。** 内容: {current_state.detail}**, また場合によっては次のステップに進んでもいいです。（次のステップの内容{self.states[min(self.current_state_index+1, len(self.states)-1)].detail}",
                current_state.title  # タイトルを追加
            )

    async def set_timer(self):
        current_state = self.states[self.current_state_index]
        if current_state.time > 0:
            self.timer = asyncio.create_task(self.timeout_handler(current_state.time))

    async def timeout_handler(self, minutes: int):
        await asyncio.sleep(minutes * 60)
        self.timeout_count += 1
        if self.timeout_count >= 2:
            await self.end_conversation()
        else:
            await self.direct_prompting_func(
                f"応答がないですが、準備中かと思われるので、進行について伺ってください。 : {self.current_state.detail}",
                self.states[self.current_state_index].title  # タイトルを追加
            )

    async def end_conversation(self):
        await self.direct_prompting_func("会話を終了します。ありがとうございました。", "終了")
        self.is_on = False
        if self.callback:
            await self.callback()

    async def run(self, is_debug: bool = False):
        self.is_on = True
        if is_debug:
            print("<Run> called")

        await self.send_next_message()

        while self.is_on:
            await asyncio.sleep(0.1)

    # check_is_explained の実装
    async def check_is_explained(self, global_responses: List[str], responses: List[str], detail: str) -> tuple[str, bool]:
        try:
            response = check_is_explained_chain.invoke({
                "global_responses": global_responses,
                "responses": responses,
                "detail": detail
            })
            return response["thought"], response["is_explained"]
        except Exception as e:
            print(f"Error in check_is_explained: {e}")
            return "Error in check_is_explained", False

    # check_is_finished の実装
    async def check_is_finished(self, global_responses: List[str], responses: List[str], detail: str, next_state_name: str) -> tuple[str, bool]:
        response = check_is_finished_chain.invoke({
            "global_responses": global_responses,
            "responses": responses,
            "detail": detail,
            "next_state_name": next_state_name
        })
        return response["thought"], response["is_finished"]

    def main(self, send_socket, get_messages):
        self.send_socket = send_socket
        self.set_callbacks(self.callback, self.direct_prompting_func)

        # 別スレッドでControllerを実行
        loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.run_controller, args=(loop, self))
        self.thread.start()

    def run_controller(self, loop, controller):
        asyncio.set_event_loop(loop)
        self.loop = loop  # イベントループを保存
        loop.run_until_complete(controller.run(is_debug=True))

    def schedule_proceed_to_next_state(self):
        """
        イベントループ内で proceed_to_next_state をスケジュールします。
        """
        if self.loop:
            asyncio.run_coroutine_threadsafe(self.proceed_to_next_state(), self.loop)
        else:
            # ループがまだ初期化されていない場合は、新たに作成
            self.loop = asyncio.new_event_loop()
            asyncio.run_coroutine_threadsafe(self.proceed_to_next_state(), self.loop)

    async def set_message(self, message):
        if "user" in message:
            await self.set_context(f"user : {message}")
        elif "assistant" in message:
            await self.set_context(f"assistant : {message}")

    def callback(self):
        best_prob_item = self.uot_controller.uot.root.get_best_prob_item()
        instruction = f"次の行動の指示出しを行ってください: {best_prob_item.name} - {best_prob_item.description}"
        self.send_socket("instruction", {"instruction": instruction, "isLendingEar": False})
        self.stop()

    def direct_prompting_func(self, prompt, title=None):
        if self.state_changed:
            # 状態変化時は 'telluser' イベントを使用
            self.send_socket("telluser", {"titles": title, "detail": prompt})
            self.state_changed = False  # 状態変化フラグをリセット
        else:
            # それ以外は 'instruction' イベントを使用
            self.send_socket("instruction", {"instruction": prompt, "isLendingEar": False})

    def stop(self):
        if self.thread and self.thread.is_alive():
            self.set_mode(False)
            self.thread.join()
            self.thread = None

# 使用例
async def main():
    async def mock_direct_message_callback(message, is_repeat=False, is_end=False):
        print(f"Direct Message: {message}")

    async def mock_callback():
        print("Conversation ended.")

    controller = LinearConversationController(fast_model)
    controller.set_callbacks(mock_callback, mock_direct_message_callback)

    asyncio.create_task(controller.run(is_debug=True))

    test_messages = [
        "assistant: はい、デイサービスの準備について説明します。",
        "user: わかりました。準備を始めます。",
        "assistant: 次は朝食についてお話しします。",
        "user: 朝食を済ませました。",
        "assistant: 洗顔と髭剃りの時間です。",
        "user: 終わりました。",
        "assistant: 着替えについて提案させていただきます。",
        "user: 着替えも完了しました。",
        "assistant: お迎えの時間が近づいていますね。",
        "user: はい、準備ができました。",
    ]

    for message in test_messages:
        await controller.set_context(message)
        await asyncio.sleep(1)

    while controller.get_mode():
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    asyncio.run(main())
