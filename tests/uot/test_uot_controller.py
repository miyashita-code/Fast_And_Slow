import asyncio
import threading
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, './')  # プロジェクトのルートディレクトリをパスに追加
from uot_modules.llm_utils import get_response_util, pydantic_to_dict
from uot_controller.controller import UoTController
from neo4j_modules.care_kg_db import CareKgDB

# コールバック関数
def callback():
    print("傾聴が終了しました。")
    global running
    running = False

# 直接プロンプト関数
def direct_prompting_func(prompt):
    print(f"**********************\nINSTRUCT : {prompt}\n**********************")

# 対話のシミュレーション
async def simulate_conversation(controller):
    while running:
        user_input = input("user: ")
        if user_input.lower() == "exit":
            break
        await controller.set_context(f"user : {user_input}")

        
        assistant_input = input("assistant : ")
        if assistant_input.lower() == "exit":
            break
        await controller.set_context(f"assistant : {assistant_input}")


# メインテスト関数
async def test_uot_controller():
    load_dotenv()
    db = CareKgDB(os.getenv("NEO4J_URI"), os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
    controller = UoTController(db)
    controller.set_callbacks(callback, direct_prompting_func)
    controller.set_contexts([])

    global running
    running = True

    # 別スレッドでUoTControllerを実行
    def run_controller(loop, controller):
        asyncio.set_event_loop(loop)
        loop.run_until_complete(controller.run(is_debug=True))

    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=run_controller, args=(loop, controller))
    thread.start()

    # 対話のシミュレーションを開始
    await simulate_conversation(controller)

    # スレッドの終了を待機
    thread.join()

if __name__ == "__main__":
    """
    try:
        asyncio.run(test_uot_controller())
    except Exception as e:
        print(e)
        running = False
        # すべてのスレッドを終了
        for thread in threading.enumerate():
            if thread != threading.main_thread():
                thread.join()
    """
    asyncio.run(test_uot_controller())


