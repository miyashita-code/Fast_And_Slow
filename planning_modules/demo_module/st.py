from typing import Callable, List, NamedTuple, Optional

import asyncio
from pydantic import BaseModel
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_fireworks import ChatFireworks
from langchain_core.runnables import RunnableSequence
from dotenv import load_dotenv
import threading

from planning_modules.demo_module.sample_states import (
    get_init_state_walk_preparation,
    get_init_state_dayservice2
)
from planning_modules.demo_module.state import State
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
even if there are no user responses to check, json以外で答えるな！一文字も追加するな！, 「次は？」とか言われたらすぐに次に行け！次の内容の話を始めもすぐに次に行け！
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
        self.state_changed = False
        self.loop = None
        self.current_state_name = self.states[0].name
        self.state_dict = {state.name: state for state in self.states}
        self._socket_emit = None  # 実際のsocket.emit関数を保持

    def set_callbacks(self, callback: Callable, direct_prompting_func: Callable):
        self.callback = callback
        self.direct_prompting_func = direct_prompting_func

    def get_init_state(self) -> List[State]:
        """ 
        Stateのハードコーディング系列を返す
        """
        # return get_init_state_iphone_manipuration()
        return get_init_state_dayservice2()


    def set_mode(self, mode: bool):
        self.is_on = mode

    def get_mode(self):
        return self.is_on

    async def set_context(self, context: str):
        #await self.__deal_user_response(context)
        pass

    async def __deal_user_response(self, response: str):
        self.global_responses_buffer.append(response)

        if self.current_state_index >= len(self.states):
            return

        if not self.is_on:
            return

        if "assistant" in response and not self.is_explained:
            print(f"global_responses_buffer: {self.global_responses_buffer}, responses_buffer: {self.responses_buffer}, detail: {self.states[self.current_state_index].description}")
            thought, result = await self.check_is_explained(self.global_responses_buffer, self.responses_buffer, self.states[self.current_state_index].description)
            print(f"Check is explained thought: {thought}")
            if result:
                self.is_explained = True
            else:
                await self.direct_prompting_func(
                    f"次の内容について可能な限り早い段階で伝えてください。ただし対話の文脈を壊さないように少し言い方を変えても構いません。内容: {self.states[self.current_state_index].description}, また場合によっては次のステップに進んでもいいです。（次のステップの内容{self.states[min(self.current_state_index+1, len(self.states)-1)].description}",
                    self.states[self.current_state_index].title  # タイトルを追加
                )
        elif "user" in response and self.is_explained:
            self.responses_buffer.append(response)
            print(f"global_responses_buffer: {self.global_responses_buffer}, responses_buffer: {self.responses_buffer}, detail: {self.states[self.current_state_index].description}, next_state: {self.states[self.current_state_index].next_state}")
            thought, is_finished = await self.check_is_finished(self.global_responses_buffer, self.responses_buffer, self.states[self.current_state_index].description, self.states[self.current_state_index].next_state)
            print(f"Check is finished thought: {thought}")
            if is_finished:
                self.responses_buffer = []
                await self.proceed_to_next_state()
                self.is_explained = False
            else:
                await self.direct_prompting_func(
                    f"次の内容について可能な限り早い段階で伝えてください。すでに伝えている場合は、ゆっくりと傾聴し積極的に反応を引き出したり追加で掘り下げて説明してください。内容: {self.states[self.current_state_index].description}, また場合によっては次のステップに進んでもいいです。（次のステップの内容{self.states[min(self.current_state_index+1, len(self.states)-1)].description}",
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
        current_state = self.state_dict.get(self.current_state_name)
        next_state_name = current_state.next_state
        if next_state_name and next_state_name in self.state_dict:
            self.current_state_name = next_state_name
            self.state_changed = True
            # フラグやバッファのリセット
            self.is_explained = False
            self.responses_buffer.clear()
            self.global_responses_buffer.clear()
            
            # 次の状態の情報を取得してクライアントに送信
            next_state = self.state_dict.get(next_state_name)
            state_info = {
                "current_state": next_state_name,
                "description": next_state.description,
                "title": next_state.title,
                "has_detail": next_state.detail_name is not None,
                "has_next": next_state.next_state is not None,
                "call_to_action": next_state.call_to_action if next_state.call_to_action else "",
                "detail_instruction": next_state.detail_instruction if next_state.detail_instruction else ""
            }
            await self.send_socket("next_state_info", {"state_info": state_info})
            
            # 次のメッセージを送信
            await self.send_next_message()
        else:
            await self.end_conversation()

    async def go_to_detail(self):
        current_state = self.state_dict.get(self.current_state_name)
        detail_name = current_state.detail_name
        if detail_name and detail_name in self.state_dict:
            self.current_state_name = detail_name
            self.state_changed = True
            # フラグやバッファのリセット
            self.is_explained = False
            self.responses_buffer.clear()
            self.global_responses_buffer.clear()
            
            # 詳細状態の情報を取得してクライアントに送信
            detail_state = self.state_dict.get(detail_name)
            state_info = {
                "current_state": detail_name,
                "description": detail_state.description,
                "title": detail_state.title,
                "is_detail": True,
                "has_next": detail_state.next_state is not None
            }
            await self.send_socket("next_state_info", {"state_info": state_info})
            
            await self.send_next_message()
        else:
            await self.send_socket("next_state_info", {"state_info": {"error": "詳細がありません"}})
            await self.send_next_message()
    
    async def back_to_start(self):
        self.current_state_name = self.states[0].name
        
        self.state_changed = True
        # フラグやバッファのリセット
        self.is_explained = False
        self.responses_buffer.clear()
        self.global_responses_buffer.clear()
        
        # 初期状態の情報を取得してクライアントに送信
        #initial_state = self.state_dict[self.states[0].name]
        #state_info = {
        #    "current_state": self.states[0].name,
        #    "description": initial_state.description,
        #    "title": initial_state.title,
        #    "has_detail": initial_state.detail_name is not None,
        #    "has_next": initial_state.next_state is not None,
        #    "is_initial": True
        #}
        #await self.send_socket("next_state_info", {"state_info": state_info})
        
        await self.send_next_message()

    async def send_next_message(self):
        current_state = self.state_dict.get(self.current_state_name)
        if current_state:
            # 次の状態の情報を取得
            next_state = self.state_dict.get(current_state.next_state)
            next_state_info = next_state.description if next_state else "終了"
            
            # 詳細状態の情報を取得
            detail_state = self.state_dict.get(current_state.detail_name)
            detail_info = detail_state.description if detail_state else None
            
            # メッセージを構築
            message = {
                "current": current_state.description,
                "next": next_state_info,
                "detail": detail_info,
                "has_detail": detail_info is not None,
                "detail_instruction": current_state.detail_instruction if detail_state else "なし"
            }
            
            # メッセージを送信
            await self.direct_prompting_func(
                f"Planing Systemから要請です。次の内容について可能な限り早い段階で伝えてください。"
                f"なお、内容が不自然な場合は文脈が壊れないように少し言い方を変えても構いません。"
                f"************************************"
                f"\n\n現在の内容: {message['current']}"
                f"\n\n補足情報: {message['detail_instruction']}"
                f"\n************************************"
                f"\n（次の内容: {message['next']}***[注意警告] これを参照した内容を話す前に適切にgo_nextなどの関数を絶対に絶対によんでください！！***）（これは本来頭の片隅にあり、堂々とこの段階で話されるべきではないので関数を読んでください！）"
                + (f"\n詳細な内容: {message['detail']}" if message['has_detail'] else ""),
                current_state.title
            )

            if current_state and current_state.call_to_action:
                # 非ブロッキングで10秒後に実行
                #asyncio.create_task(self._delayed_call_to_action(current_state.call_to_action))
                pass

    async def _delayed_call_to_action(self, call_to_action: str):
        """10秒遅延してcall_to_actionを送信する内部メソッド"""
        await asyncio.sleep(10)
        await self.send_socket("call_to_action", {"action_description": call_to_action})

    async def send_call_to_action(self, call_to_action: str):
        """非推奨: 代わりに_delayed_call_to_actionを使用"""
        await self.send_socket("call_to_action", {"action_description": call_to_action})

    async def send_socket(self, event_name: str, data: dict):
        """ソケットイベントを送信"""
        if self._socket_emit:
            if asyncio.iscoroutinefunction(self._socket_emit):
                await self._socket_emit(event_name, data)
            else:
                self._socket_emit(event_name, data)

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
                f"応答がないですが、準備中かと思われるので、進行について伺ってください。 : {self.current_state.description}",
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
        """同期的なメインエントリーポイント"""
        # 非同期関数をラップして保存
        async def socket_emit_wrapper(event_name: str, data: dict):
            if asyncio.iscoroutinefunction(send_socket):
                await send_socket(event_name, data)
            else:
                send_socket(event_name, data)
        
        self._socket_emit = socket_emit_wrapper
        self.set_callbacks(self.callback, self.direct_prompting_func)
        
        # 新しいイベントループを作成
        self.loop = asyncio.new_event_loop()
        
        # 別スレッドでControllerを実行
        self.thread = threading.Thread(target=self._run_async_main, args=(self.loop,))
        self.thread.start()

    def _run_async_main(self, loop):
        """非同期処理を実行する内部メソッド"""
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.run(is_debug=True))
        except Exception as e:
            print(f"Error in _run_async_main: {e}")
            self.stop()
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
            except Exception as e:
                print(f"Error while closing loop: {e}")

    def run_controller(self, loop, controller):
        """非推奨: 代わりに_run_async_mainを使用"""
        try:
            asyncio.set_event_loop(loop)
            self.loop = loop
            loop.run_until_complete(controller.run(is_debug=True))
        except Exception as e:
            print(f"Error in run_controller: {e}")
            self.stop()

    def handle_socket_event(self, event_name: str):
        print(f"handle_socket_event called with event_name: {event_name}")
        try:
            if not self.loop or self.loop.is_closed():
                print("Warning: Event loop is not available or closed")
                return

            if event_name == 'next_state':
                future = asyncio.run_coroutine_threadsafe(self.proceed_to_next_state(), self.loop)
                future.add_done_callback(lambda f: self._handle_future_result(f, "proceed_to_next_state"))
            elif event_name == 'go_detail':
                future = asyncio.run_coroutine_threadsafe(self.go_to_detail(), self.loop)
                future.add_done_callback(lambda f: self._handle_future_result(f, "go_detail"))
            elif event_name == 'back_to_start':
                future = asyncio.run_coroutine_threadsafe(self.back_to_start(), self.loop)
                future.add_done_callback(lambda f: self._handle_future_result(f, "back_to_start"))
        except Exception as e:
            print(f"Error in handle_socket_event: {e}")
            # エラー時もクライアントに通知
            if hasattr(self, 'send_socket'):
                error_info = {"error": str(e)}
                asyncio.run_coroutine_threadsafe(
                    self.send_socket("next_state_info", {"state_info": error_info}),
                    self.loop
                )

    def _handle_future_result(self, future, operation_name):
        try:
            result = future.result()
            print(f"Operation {operation_name} completed successfully")
        except Exception as e:
            print(f"Error in {operation_name}: {e}")

    def stop(self):
        try:
            if self.loop and not self.loop.is_closed():
                self.loop.stop()
            if self.thread and self.thread.is_alive():
                self.set_mode(False)
                self.thread.join(timeout=5)  # タイムアウトを設定
                self.thread = None
        except Exception as e:
            print(f"Error in stop: {e}")

    async def set_message(self, message):
        print(f"set_message called with message: {message}")
        if "user" in message:
            await self.set_context(f"user : {message}")
        elif "assistant" in message:
            await self.set_context(f"assistant : {message}")

    async def callback(self):
        best_prob_item = self.uot_controller.uot.root.get_best_prob_item()
        instruction = f"次の行動の指示出しを行ってください: {best_prob_item.name} - {best_prob_item.description}"
        await self.send_socket("instruction", {"instruction": instruction, "isLendingEar": False})
        self.stop()

    async def direct_prompting_func(self, prompt, title=None):
        if self.state_changed:
            # 状態変化時は 'telluser' イベントを使用
            await self.send_socket("telluser", {"titles": title, "detail": prompt})
            self.state_changed = False
        else:
            # それ以外は 'instruction' イベントを使用
            await self.send_socket("instruction", {"instruction": prompt, "isLendingEar": False})
    

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
