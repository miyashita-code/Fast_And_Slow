import sys
import os


from uot_controller.controller import UoTController

from neo4j_modules.care_kg_db import CareKgDB
import asyncio
import threading

class LendingEarController:
    def __init__(self, db: CareKgDB):
        self.db = db
        self.uot_controller = UoTController(db)
        self.thread = None

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

    def set_message(self, message):
        if "user" in message:
            self.uot_controller.set_context(f"user : {message}")
        elif "assistant" in message:
            self.uot_controller.set_context(f"assistant : {message}")

    def callback(self):
        best_prob_item = self.uot_controller.uot.root.get_best_prob_item()
        instruction = f"次の行動の指示出しを行ってください: {best_prob_item.name} - {best_prob_item.description}"
        self.send_socket("instruction", {"instruction": instruction, "isLendingEar": False})
        self.stop()

    def direct_prompting_func(self, prompt):
        self.send_socket("instruction", {"instruction": prompt, "isLendingEar": True})

    def stop(self):
        if self.thread and self.thread.is_alive():
            self.uot_controller.set_mode(False)
            self.thread.join()
            self.thread = None
