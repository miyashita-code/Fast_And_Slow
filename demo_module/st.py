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
even if there are no user responses to check, json以外で答えるな！一文字も追加するな！
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

    def set_callbacks(self, callback: Callable, direct_prompting_func: Callable):
        self.callback = callback
        self.direct_prompting_func = direct_prompting_func

    def get_init_state(self) -> List[State]:
        return [
            State(detail="デイサービスの準備について, デーサービスの迎えが9:00に来るので、その前に外出の準備を済ませましょう。", name="初めの説明", time=0, next_state="朝食"),
            State(detail="まずは、朝食を済ませましょう。", name="朝食", time=1, next_state="洗顔と髭剃り"),
            State(detail="洗顔と髭剃りをしましょう。歯磨きもお忘れなく。ひげをそるときは、剃刀ではなく、赤の電動シェイバーがおすすめです。（剃刀負けしなくて便利ですね。）", name="洗顔と髭剃り", time=1, next_state="着替え"),
            State(detail="次に、服装について考えましょう。今日は暑くもなく、少し涼しいので薄手の長袖か半袖が良いかもしれませんね。", name="着替え", time=1, next_state="お迎え待ち"),
            State(detail="8時50分になったら、ちょうどよい時間なので、家の前でデイサービスのお迎えを待ちましょう。", name="お迎え待ち", time=0, next_state="終了"),
            State(detail="お気を付けて、良い一日を！", name="終了", time=0, next_state="終了"),
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

        if "assistant" in response and not self.is_explained:
            print(f"global_responses_buffer: {self.global_responses_buffer}, responses_buffer: {self.responses_buffer}, detail: {self.states[self.current_state_index].detail}")
            thought, result = await self.check_is_explained(self.global_responses_buffer, self.responses_buffer, self.states[self.current_state_index].detail)
            print(f"Check is explained thought: {thought}")
            if result:
                self.is_explained = True
            else:
                await self.direct_prompting_func(f"次の内容について可能な限り早い段階で伝えてください。ただし対話の文脈を壊さないように少し言い方を変えても構いません。内容: {self.states[self.current_state_index].detail}")
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
                await self.direct_prompting_func(f"次の内容について可能な限り早い段階で伝えてください。すでに伝えている場合は、ゆっくりと傾聴し積極的に反応を引き出したり追加で掘り下げて説明してください。内容: {self.states[self.current_state_index].detail}")

        if self.timer:
            self.timer.cancel()

        if self.current_state_index < len(self.states):
            current_state = self.states[self.current_state_index]
            if current_state.time > 0:
                self.timeout_count = 0
                await self.set_timer()
            else:
                await self.proceed_to_next_state()

    async def proceed_to_next_state(self):
        self.current_state_index += 1
        if self.current_state_index >= len(self.states):
            await self.end_conversation()
        else:
            await self.send_next_message()

    async def send_next_message(self):
        if self.current_state_index < len(self.states):
            current_state = self.states[self.current_state_index]
            await self.direct_prompting_func(f"Planing Systemから要請です。次の内容について可能な限り早い段階で伝えてください。なお、内容が不自然な場合は文脈が壊れないように少し言い方を変えても構いません。** 内容: {current_state.detail}**")

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
            await self.direct_prompting_func(f"応答がないですが、準備中かと思われるので、進行について伺ってください。 : {self.current_state.detail}")

    async def end_conversation(self):
        await self.direct_prompting_func("会話を終了します。ありがとうございました。")
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
        response = check_is_explained_chain.invoke({
            "global_responses": global_responses,
            "responses": responses,
            "detail": detail
        })
        return response["thought"], response["is_explained"]

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
        loop.run_until_complete(controller.run(is_debug=True))

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

    def direct_prompting_func(self, prompt):
        self.send_socket("instruction", {"instruction": prompt, "isLendingEar": True})

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