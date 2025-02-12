import os
import sys
import asyncio
import json
import websockets
from dotenv import load_dotenv
import contextlib
from typing import Optional

sys.path.insert(0, './')

from uot_modules.item import Item
from neo4j_modules.care_kg_db import CareKgDB
from state_machine_modules.instruction_graph import InstructionGraph
from state_machine_modules.io_manager import IOManager

class TestWebSocketServer:
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.messages = asyncio.Queue()
        self.server = None
        self.is_running = False
        self.clients = set()
        self.client_connected = asyncio.Event()
        self.connection_ready = asyncio.Event()

    async def handler(self, websocket):
        """WebSocket接続を処理"""
        try:
            self.clients.add(websocket)
            self.client_connected.set()
            print(f"Client connected. Total clients: {len(self.clients)}")
            
            try:
                async for message in websocket:
                    print(f"Server received: {message}")
                    try:
                        data = json.loads(message)
                        await self.messages.put(data)
                        
                        # メッセージタイプに基づいて適切なレスポンスを生成
                        action_type = data.get("type", "unknown")
                        node_name = data.get("data", {}).get("node", "")
                        
                        response = {
                            "type": action_type,
                            "current_node": node_name,
                            "success": True,
                            "children": [
                                "コートを着る",
                                "コートのボタンを留める"
                            ] if action_type == "go_next" else []
                        }
                        
                        await websocket.send(json.dumps(response))
                        print(f"Server sent response: {response}")
                        
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
                    except Exception as e:
                        print(f"Error processing message: {e}")
            except websockets.exceptions.ConnectionClosed:
                print("Client connection closed normally")
            finally:
                await self._cleanup_client(websocket)
                
        except Exception as e:
            print(f"Error in handler: {str(e)}")
            await self._cleanup_client(websocket)

    async def _cleanup_client(self, websocket):
        """クライアント接続のクリーンアップ"""
        if websocket in self.clients:
            try:
                self.clients.remove(websocket)
                if not self.clients:
                    self.client_connected.clear()
                print(f"Client disconnected. Remaining clients: {len(self.clients)}")
            except Exception as e:
                print(f"Error during client cleanup: {str(e)}")
        else:
            print("Client already disconnected")

    async def start(self):
        """WebSocketサーバーを起動"""
        if not self.is_running:
            try:
                self.server = await websockets.serve(
                    self.handler,
                    self.host,
                    self.port,
                    ping_interval=20,
                    ping_timeout=10
                )
                self.is_running = True
                self.connection_ready.set()
                print(f"WebSocket server started on ws://{self.host}:{self.port}")
            except Exception as e:
                print(f"Error starting server: {e}")
                raise

    async def broadcast(self, message):
        if not self.clients:
            print("Waiting for client connection...")
            try:
                await asyncio.wait_for(self.client_connected.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                print("Timeout waiting for client connection")
                return False
        
        success = False
        for client in list(self.clients):
            try:
                await client.send(json.dumps(message))
                success = True
            except Exception as e:
                print(f"Error broadcasting to client: {e}")
                self.clients.remove(client)
                if not self.clients:
                    self.client_connected.clear()
        
        return success

    async def stop(self):
        """サーバーを停止し、すべての接続をクリーンアップ"""
        if self.is_running and self.server:
            try:
                # すべてのクライアントを切断
                for client in list(self.clients):
                    try:
                        await client.close()
                    except Exception as e:
                        print(f"Error closing client connection: {e}")
                self.clients.clear()
                self.client_connected.clear()
                
                # サーバーを停止
                self.server.close()
                await self.server.wait_closed()
                self.is_running = False
                self.connection_ready.clear()
                print("WebSocket server stopped cleanly")
            except Exception as e:
                print(f"Error stopping server: {e}")
                raise

class InstructionFlowSimulator:
    def __init__(self):
        load_dotenv()
        self.db = CareKgDB(
            os.getenv("NEO4J_URI"),
            os.getenv("NEO4J_USERNAME"),
            os.getenv("NEO4J_PASSWORD")
        )
        self.io_manager = IOManager()
        self.items = None
        self.is_debug = True
        self.websocket = None
        self._server = None
        self.instruction_graph = None

    async def setup(self):
        """初期セットアップを行う"""
        try:
            # WebSocketサーバーの起動
            self._server = TestWebSocketServer()
            await self._server.start()
            
            # サーバーの準備完了を待機
            await self._server.connection_ready.wait()
            print("Server is ready for connections")
            
            # クライアント接続の確立を試行
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    self.websocket = await websockets.connect(
                        f"ws://{self._server.host}:{self._server.port}",
                        ping_interval=20,
                        ping_timeout=10
                    )
                    self.io_manager.set_websocket(self.websocket)
                    print("WebSocket connection established")
                    
                    # 接続確立を確認
                    await asyncio.sleep(1)
                    if self._server.client_connected.is_set():
                        print("Client connection confirmed")
                        return True
                    
                except Exception as e:
                    print(f"Connection attempt {attempt + 1} failed: {e}")
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(1)
                    else:
                        raise RuntimeError("Failed to establish WebSocket connection")
            
            raise RuntimeError("Failed to confirm client connection")
            
        except Exception as e:
            print(f"Setup failed: {e}")
            raise

    async def run_simulation(self):
        try:
            print("\n=== Starting Instruction Flow Simulation ===")

            demo_items = [
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


            # アイテムの説明を取得
            tasks = [self.get_item_description(item) for item in demo_items]
            self.items = [item for item in await asyncio.gather(*tasks) if item is not None]

            # InstructionGraphの初期化と構築
            self.instruction_graph = InstructionGraph(self.db, self.io_manager, is_debug=self.is_debug)
            await self.instruction_graph.construct_graph(self.items)

            if not self.instruction_graph.tree_root:
                raise RuntimeError("Failed to construct instruction tree")

            print("\n=== Starting Interaction Flow Test ===")
            
            # ルートノードから実行開始（center_targetを指定）
            await self.instruction_graph.tree_root.run(center_target="上着を選ぶ")
            
            print("\n=== Test Completed ===")

        except Exception as e:
            print(f"Simulation failed: {e}")
            raise
        finally:
            await self.cleanup()

    async def get_item_description(self, item):
        """アイテムの説明を取得"""
        try:
            item.description = await self.db.get_item_description_async(item.name)
            context_info = await self.db.get_related_nodes(item.name)
            item.context_info = context_info
            return item
        except Exception as e:
            print(f"Error in get_item_description for {item.name}: {e}")
            return None

    async def cleanup(self):
        try:
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
            
            if self._server:
                await self._server.stop()
                self._server = None
            
            await self.io_manager.close()
            await self.db.close()
        except Exception as e:
            print(f"Cleanup failed: {e}")

async def main():
    simulator = InstructionFlowSimulator()
    try:
        await simulator.run_simulation()
    except Exception as e:
        print(f"Main execution failed: {e}")
    finally:
        await simulator.cleanup()

if __name__ == "__main__":
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        print("Starting test execution...")
        asyncio.run(main())
        print("Test execution completed.")
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
