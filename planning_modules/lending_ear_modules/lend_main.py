import sys
import os


from planning_modules.lending_ear_modules.uot_modules.uot_controller.controller import UoTController

from neo4j_modules.care_kg_db import CareKgDB
import asyncio
import threading
import traceback

class LendingEarController:
    def __init__(self, db: CareKgDB):
        self.db = db
        self.uot_controller = UoTController(db)
        self.thread = None
        self.is_waiting_for_answer = False  # 質問待ち状態を管理

    def main(self, send_socket, get_messages):
        self.send_socket = send_socket
        self.uot_controller.set_callbacks(self.callback, self.direct_prompting_func)
        self.uot_controller.set_contexts(get_messages())

        # 別スレッドでUoTControllerを実行
        loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.run_controller, args=(loop, self.uot_controller))
        self.thread.start()

    def run_controller(self, loop, controller):
        asyncio.set_event_loop(loop)
        loop.run_until_complete(controller.run(is_debug=True))

    async def set_message(self, message):
        """
        メッセージを設定し、必要に応じて質問待ち状態を更新
        """
        if "user" in message:
            await self.uot_controller.set_context(f"user : {message}")
            # ユーザーからの回答を受け取ったら質問待ち状態を解除
            self.is_waiting_for_answer = False
        elif "assistant" in message:
            await self.uot_controller.set_context(f"assistant : {message}")

    def callback(self):
        best_prob_item = self.uot_controller.uot.root.get_best_prob_item()
        instruction = f"次の行動の指示出しを行ってください: {best_prob_item.name} - {best_prob_item.description}"
        self.send_socket("instruction", {"instruction": instruction, "isLendingEar": False})
        self.stop()

    def direct_prompting_func(self, prompt):
        # イベント名を "telluser" に変更し、データを調整
        self.send_socket("telluser", {"titles": "状況整理のために質問中...", "detail": prompt})

    def stop(self):
        if self.thread and self.thread.is_alive():
            self.uot_controller.set_mode(False)
            self.thread.join()
            self.thread = None

    async def request_next_question(self):
        """
        次の質問を要求する
        """
        try:
            if hasattr(self.uot_controller, 'uot'):
                # 現在の状態が質問待ちでない場合のみ次の質問を要求
                if not self.is_waiting_for_answer:
                    next_question = await self.uot_controller.uot.get_question()
                    if next_question:
                        self.is_waiting_for_answer = True
                        self.direct_prompting_func(
                            f"次の質問について可能な限り早い段階で伺ってください. "
                            f"ただし対話の文脈を壊さないように少し言い方を変えても構いません. "
                            f"質問 : {next_question}"
                        )
                        print(f"<Requested next question>: {next_question}")
        except Exception as e:
            print(f"Error in request_next_question: {e}")
            traceback.print_exc()
