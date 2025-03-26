import os
import sys
import asyncio
import time
from dotenv import load_dotenv
import contextlib

sys.path.insert(0, './')

from uot_modules.item import Item
from neo4j_modules.care_kg_db import CareKgDB
from state_machine_modules.instruction_graph import InstructionGraph


class TestConstructInsTree:
    def __init__(self, is_debug: bool = False):
        load_dotenv()
        self.db = CareKgDB(
            os.getenv("NEO4J_URI"),
            os.getenv("NEO4J_USERNAME"),
            os.getenv("NEO4J_PASSWORD")
        )
        self.items = None
        self.is_debug = is_debug

    def debug_print(self, message: str):
        if self.is_debug:
            print(f"[DEBUG, TestConstructInsTree] {message}")

    async def get_item_description(self, item):
        try:
            item.description = await self.db.get_item_description_async(item.name)
            print(f"description: {item.description}")
            context_info = await self.db.get_related_nodes(item.name)
            item.context_info = context_info  # context_infoをItemに設定
            print(f"global_context: {context_info['global_context']}")
            print(f"local_context: {context_info['local_context']}")
        except Exception as e:
            self.debug_print(f"Error in get_item_description for {item.name}: {e}")
            import traceback
            self.debug_print(traceback.format_exc())  # 詳細なトレースバックを出力
            return None
        return item

    async def set_demo_inits_items(self):
        #demo_items = self.get_demo_const_items()
        demo_items = await self.get_all_items()

        self.debug_print(f"demo_items: {demo_items}")

        tasks = [self.get_item_description(item) for item in demo_items]
        results = await asyncio.gather(*tasks)

        self.debug_print(f"results: {results}")

        # Noneを除外
        demo_items = [item for item in results if item is not None]

        self.debug_print(f"demo_items: {demo_items}")

        self.items = demo_items

        self.debug_print(f"self.items: {self.items}")

    def get_demo_const_items(self):
        demo_const_items = [
            Item(name="デイサービス準備", description="", p_s=0.000289),
            Item(name="身だしなみの準備", description="", p_s=0.145295),
            Item(name="顔回りの手入れ", description="", p_s=0.000133),
            Item(name="服装の準備", description="", p_s=0.204981),
            Item(name="顔を洗う", description="", p_s=0.003335),
            Item(name="歯を磨く", description="", p_s=0.000093),
            Item(name="ひげを剃る", description="", p_s=0.000015),
            Item(name="コートを選ぶ", description="", p_s=0.000850),
            Item(name="コートを着る", description="", p_s=0.019574),
            Item(name="リラックス", description="", p_s=0.000005),
            Item(name="散歩", description="", p_s=0.000007),
            Item(name="着替え", description="", p_s=0.197973),
            Item(name="靴下を見つける", description="", p_s=0.000593),
            Item(name="上着を選ぶ", description="", p_s=0.206912),
            Item(name="トイレに行く", description="", p_s=0.000015),
            Item(name="靴を履く", description="", p_s=0.071192),
            Item(name="棚の引き出しを開ける", description="", p_s=0.000001),
            Item(name="他の引き出しを探す", description="", p_s=0.000000),
            Item(name="窓の縁を確認する", description="", p_s=0.000001),
            Item(name="コートを着る", description="", p_s=0.004651),
            Item(name="コートのボタンを留める", description="", p_s=0.004066),
            Item(name="1階の靴箱に向かう", description="", p_s=0.000078),
            Item(name="靴箱から靴を取り出す", description="", p_s=0.007592),
            Item(name="スリッパを靴箱に入れる", description="", p_s=0.000001),
            Item(name="靴を履く", description="", p_s=0.018795),
            Item(name="靴下が見つからない", description="", p_s=0.000145),
            Item(name="ファスナーの締め方がわからない", description="", p_s=0.000031),
            Item(name="外出の準備で不安になる", description="", p_s=0.048971),
            Item(name="靴箱を間違える", description="", p_s=0.000021),
            Item(name="靴下が見つからない不安", description="", p_s=0.007264),
            Item(name="コートのファスナーが締められない戸惑い", description="", p_s=0.007195),
            Item(name="外出の準備の不安", description="", p_s=0.031815),
            Item(name="靴箱を間違える焦り", description="", p_s=0.000300),
            Item(name="靴下が見つからない状況", description="", p_s=0.000244),
            Item(name="外の気温が低い状況", description="", p_s=0.000143),
            Item(name="おなかが痛む", description="", p_s=0.000011),
            Item(name="下痢", description="", p_s=0.000587),
            Item(name="不安な気持ち", description="", p_s=0.000294),
            Item(name="のどの渇き", description="", p_s=0.000288),
            Item(name="お腹の状態を確認する", description="", p_s=0.001093),
            Item(name="トイレに行くよう促す", description="", p_s=0.000296),
            Item(name="気持ちに寄り添う", description="", p_s=0.000000),
            Item(name="不安な気持ちを和らげる", description="", p_s=0.000006),
            Item(name="飲み物を飲む", description="", p_s=0.000000),
            Item(name="冷蔵庫から飲み物を取り出す", description="", p_s=0.000000),
            Item(name="不明(その他)", description="", p_s=0.014850)
        ]

        return demo_const_items
    
    async def get_all_items(self):
        neo4j_items = await self.db.get_uot_nodes()
        items = [Item(name=node.get('name'), description=node.get('description'), p_s=0.0) for node in neo4j_items]
        return items

    async def test_center_node_validation(self):
        """センターノードの検証テスト"""
        # アイテムの初期化
        await self.set_demo_inits_items()
        
        # 存在するノードでのテスト
        valid_center = "上着を選ぶ"
        graph = InstructionGraph(self.items, self.io_manager, valid_center)
        await graph.construct_graph()
        assert graph.center_node is not None, f"センターノード '{valid_center}' が見つかりませんでした"
        
        # 存在しないノードでのテスト
        invalid_center = "存在しない行動"
        graph_invalid = InstructionGraph(self.items, self.io_manager, invalid_center)
        await graph_invalid.construct_graph()
        assert graph_invalid.center_node is None, f"存在しないはずのセンターノード '{invalid_center}' が見つかりました"

    async def run_tests(self):
        """全テストケースを実行"""
        await self.test_center_node_validation()
        print("Center node validation test completed.")
        
        # その他のテストケース...

    async def close(self):
        await self.db.close()

async def test_instruction_graph():
    test = TestConstructInsTree(is_debug=True)

    def mock_send_socket(event_name: str, data: dict):
        print(f"send_socket: {data}")

    # デバッグ出力を追加
    print("\n=== Starting InstructionGraph Test ===")

    # デモ用のアイテムを設定
    await test.set_demo_inits_items()
    print(f"Demo items count: {len(test.items) if test.items else 0}")

    # InstructionGraph を作成（global_itemsを渡す）
    ins_graph = InstructionGraph(
        kg_db=test.db,
        send_socket=mock_send_socket,
        global_items=test.items,  # ここでglobal_itemsを渡す
        is_debug=True
    )
    print(f"Created InstructionGraph instance: {ins_graph}")

    # グラフ構築前の状態確認
    print(f"Before construct_graph - virtual_root: {ins_graph.virtual_root}")
    print(f"Before construct_graph - top_nodes: {ins_graph.top_nodes}")

    # グラフを構築
    center_node_name = "prepare_for_toreliha"
    await ins_graph.construct_graph(center_node_name)
    
    # グラフ構築後の状態確認
    print(f"After construct_graph - virtual_root: {ins_graph.virtual_root}")
    print(f"After construct_graph - top_nodes: {ins_graph.top_nodes}")

    # グラフを可視化
    ins_graph.visualize_graph()


    # tree_rootの代わりにvirtual_rootを使用
    if ins_graph.virtual_root:
        ins_graph.debug_print_tree()

        def process_finished_callback():
            print("Process has finished.")

        # virtual_rootにコールバックを設定
        ins_graph.virtual_root.process_finished_callback = process_finished_callback

        # ノードの処理を開始
        task = asyncio.create_task(ins_graph.virtual_root.run())

        # イベントの処理をシミュレート
        await asyncio.sleep(0.1)
    else:
        print("Error: virtual_root is not set. construct_graph may have failed.")

    # 明示的にデータベース接続をクローズ
    await test.close()

if __name__ == "__main__":
    # イベントループを手動で管理
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    loop = asyncio.get_event_loop()
    try:
        start_time = time.time()
        loop.run_until_complete(test_instruction_graph())
        end_time = time.time()
        
        execution_time = end_time - start_time
        print(f"実行時間: {execution_time:.2f}秒")
    finally:
        # 未完了のタスクを完了させる
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                loop.run_until_complete(task)
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()




