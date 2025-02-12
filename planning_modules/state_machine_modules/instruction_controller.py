# state_machine_modules/instruction_controller.py

import eventlet
from eventlet.green import threading
from typing import Optional
import traceback
from functools import partial
from concurrent.futures import ThreadPoolExecutor

from planning_modules.state_machine_modules.instruction_graph import InstructionGraph
from neo4j_modules.care_kg_db import CareKgDB
from .base_node import BaseNode


class InstructionController:
    """
    複数トップノード + 仮想ルート
    BackendProcess から:
      - .main(center_node_name=...) で .construct_graph -> .run
      - .set_message(...) でユーザ入力を top_node へ伝える
      - .stop() で終了
    """

    def __init__(
        self,
        send_socket,       # WebSocket送信用関数
        kg_db: CareKgDB,
        is_debug: bool = False
    ):
        self.kg_db = kg_db
        self.is_debug = is_debug
        self._original_send_socket = send_socket
        self.send_socket = self._original_send_socket
        
        self.instruction_graph = InstructionGraph(
            kg_db=self.kg_db,
            send_socket=self.send_socket,
            is_debug=is_debug
        )
        
        self._running = False
        self.state_changed = False
        BaseNode.send_socket = self._original_send_socket

    def debug_print(self, msg: str):
        if self.is_debug:
            print(f"[InstructionController] {msg}")

    def main(self, get_messages):
        """メインエントリーポイント"""
        if self._running:
            self.stop()
            
        self._running = True
        
        # PINGの送信を試みる（デバッグ用）
        self.send_socket('custom_ping', '4')
        print("##### >>> [DEBUG:InstructionController] Sent PING 4")
        
        # eventletグリーンスレッドで実行
        self.green_thread = eventlet.spawn(self._run_main_loop)

    def _run_main_loop(self):
        """メインループ"""
        try:
            # グラフの構築
            print("##### >>> [DEBUG:InstructionController] Starting graph construction")
            self.instruction_graph.construct_graph_sync(None)
            print("##### >>> [DEBUG:InstructionController] Graph construction completed")
            
            # グラフを実行
            print("##### >>> [DEBUG:InstructionController] Starting graph execution")
            while self._running:
                try:
                    result = self.instruction_graph.run_sync()
                    if result == "reset":
                        print("##### >>> [DEBUG:InstructionController] Reset requested")
                        self.instruction_graph.construct_graph_sync(None)
                        continue
                    if not self._running:
                        break
                    eventlet.sleep(1)  # 次のループまで少し待つ
                except Exception as e:
                    print(f"Error in graph execution: {e}")
                    traceback.print_exc()
                    break
                
        except Exception as e:
            print(f"Error in main loop: {e}")
            traceback.print_exc()
        finally:
            self._running = False

    def stop(self):
        """安全な停止処理"""
        self._running = False
        if hasattr(self, 'green_thread'):
            self.green_thread.kill()

    def set_message(self, message: str):
        """メッセージ処理"""
        self.debug_print(f"set_message => {message}")
        for node in self.instruction_graph.top_nodes:
            node.handle_message_sync(message)  # 同期バージョンを呼び出す

    def set_callbacks(self, callback_function):
        """コールバック関数の設定"""
        self.callback_function = callback_function

    def direct_prompting_func(self, prompt: str, title: Optional[str] = None):
        """統合されたプロンプト送信関数"""
        if self.state_changed:
            self.send_socket("next_state_info", {
                "current_state": "prompt",
                "description": prompt,
                "title": title or "プロンプト",
                "has_detail": False,
                "has_next": False
            })
            self.state_changed = False
        else:
            self.send_socket("instruction", {
                "instruction": prompt,
                "isLendingEar": False
            })

    async def proceed_to_next_state(self):
        """状態遷移処理"""
        current_state = self.state_dict.get(self.current_state_name)
        if not current_state:
            error_state = {
                "current_state": "error",
                "description": "Invalid state transition",
                "title": "エラー",
                "has_detail": False,
                "has_next": False
            }
            self.send_socket("next_state_info", error_state)
            return

        next_state_name = current_state.next_state
        if next_state_name and next_state_name in self.state_dict:
            next_state = self.state_dict.get(next_state_name)
            state_info = {
                "current_state": next_state_name,
                "description": next_state.description,
                "title": next_state.title,
                "has_detail": next_state.detail_name is not None,
                "has_next": next_state.next_state is not None,
                "call_to_action": next_state.call_to_action or "",
                "detail_instruction": next_state.detail_instruction or ""
            }
            self.send_socket("next_state_info", state_info)
            self.send_socket("custom_ping", "")
            await self.send_next_message()
        else:
            error_state = {
                "current_state": "error",
                "description": "No next state available",
                "title": "エラー",
                "has_detail": False,
                "has_next": False
            }
            self.send_socket("next_state_info", error_state)

    def handle_socket_event(self, event_name: str):
        """
        Socket.IOイベントの処理
        """
        print(f"\n##### >>> [DEBUG:InstructionController] Received socket event: {event_name}")
        
        if not self.instruction_graph:
            print("##### >>> [DEBUG:InstructionController] No instruction graph available!")
            return
            
        if not self.instruction_graph.virtual_root:
            print("##### >>> [DEBUG:InstructionController] No virtual root in graph!")
            return
            
        print(f"##### >>> [DEBUG:InstructionController] Current virtual_root children: {[node.name for node in self.instruction_graph.virtual_root.children]}")
        
        # イベントをグラフの各ノードに伝播
        for node in self.instruction_graph.virtual_root.children:
            print(f"##### >>> [DEBUG:InstructionController] Setting event flag '{event_name}' for node: {node.name}")
            if event_name == 'next_state':
                node.set_event_flag('go_next')
            elif event_name == 'go_detail':
                node.set_event_flag('go_detail')
            elif event_name == 'back_to_start':
                node.set_event_flag('back_to_start')
