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
        self._selected_candidate = None  # 選択された候補を保持
        
        self.instruction_graph = InstructionGraph(
            kg_db=self.kg_db,
            send_socket=self.send_socket,
            is_debug=is_debug
        )
        
        self._running = False
        self.state_changed = False
        BaseNode.send_socket = self._original_send_socket
        
        print("\n" + "="*80)
        print("🎮 INSTRUCTION CONTROLLER INITIALIZED")
        print("="*80)

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
            # グラフの実行のみを行う（構築は行わない）
            print("##### >>> [DEBUG:InstructionController] Starting graph execution")
            while self._running:
                try:
                    result = self.instruction_graph.run_sync()
                    if result == "reset":
                        print("##### >>> [DEBUG:InstructionController] Reset requested")
                        # リセット時は同じ候補で再構築
                        self.instruction_graph.construct_graph_sync(self._selected_candidate)
                        continue
                    if not self._running:
                        break
                    eventlet.sleep(1)
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

    def on_client_connect(self, sid=None):
        """クライアント接続時の処理"""
        print("\n" + "="*80)
        print(f"🔌 CLIENT CONNECTED! (SID: {sid})")
        print("-"*40)
        
        try:
            # 接続確認のPINGを送信
            self.send_socket('custom_ping', '4')
            print("📡 Sent connection confirmation PING")
            
            # 候補を送信
            print("🎯 Sending instruction candidates...")
            self._send_instruction_candidates()
            
        except Exception as e:
            print(f"❌ Error in on_client_connect: {str(e)}")
            traceback.print_exc()
        finally:
            print("="*80)

    def handle_socket_event(self, event_name: str, data: dict = None):
        """Socket.IOイベントの処理"""
        print(f"\n##### >>> [DEBUG:InstructionController] Received socket event: {event_name}")
        
        if event_name == "start_instruction":
            # データなしのstart_instructionイベントを拒否
            if not data or "selected_candidate" not in data:
                self.debug_print("⚠️ 警告: データなしのstart_instructionイベントを無視します")
                return False
                
            # 有効なデータを持つイベントのみ処理
            self._selected_candidate = data["selected_candidate"]
            self.debug_print(f"🎯 選択された候補: {self._selected_candidate}")
            self.handle_start_instruction(self._selected_candidate)
            return True
            
        if not self.instruction_graph:
            print("##### >>> [DEBUG:InstructionController] No instruction graph available!")
            return False
            
        if not self.instruction_graph.virtual_root:
            print("##### >>> [DEBUG:InstructionController] No virtual root in graph!")
            return False
            
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

    def _send_instruction_candidates(self):
        """Activityクラスのトップノード候補を取得してクライアントに送信"""
        try:
            print("\n" + "="*80)
            print("🔍 FETCHING INSTRUCTION CANDIDATES")
            print("="*80)
            
            candidates = self.kg_db.get_activity_top_nodes()
            
            print("\n📋 CANDIDATES RETRIEVED:")
            print("-"*40)
            if candidates:
                for i, candidate in enumerate(candidates, 1):
                    print(f"\n🔸 Candidate #{i}:")
                    print(f"   Name: {candidate['name']}")
                    print(f"   Name (JP): {candidate.get('name_jp', 'N/A')}")
                    print(f"   Time to Achieve: {candidate.get('time_to_achieve', 'N/A')}")
                    print(f"   Description: {candidate.get('description', 'N/A')[:100]}...")
                    print(f"   {'-'*40}")
                
                print(f"\n📤 SENDING {len(candidates)} CANDIDATES TO CLIENT")
                print(f"="*80)
                
                self.send_socket("instruction_candidates", {
                    "candidates": candidates
                })
                self.debug_print(f"✅ Successfully sent {len(candidates)} instruction candidates")
            else:
                print("\n⚠️  NO CANDIDATES FOUND")
                print("="*80)
                self.debug_print("No instruction candidates found")
                
        except Exception as e:
            print("\n❌ ERROR IN INSTRUCTION CANDIDATES")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("="*80)
            self.debug_print(f"Error sending instruction candidates: {e}")
            traceback.print_exc()

    def handle_start_instruction(self, selected_candidate: str):
        """選択された候補でグラフを構築して実行開始"""
        try:
            if not selected_candidate:
                self.debug_print("Error: No candidate selected")
                return
                
            self.debug_print(f"Starting instruction with candidate: {selected_candidate}")
            
            # 既存の実行があれば停止
            if self._running:
                self.stop()
            
            self._running = True
            self._selected_candidate = selected_candidate  # 候補を保存
            
            # グラフを構築（選択された候補をcenter_nodeとして使用）
            print("##### >>> [DEBUG:InstructionController] Starting graph construction")
            self.instruction_graph = InstructionGraph(
                kg_db=self.kg_db,
                send_socket=self.send_socket,
                is_debug=self.is_debug
            )
            self.instruction_graph.construct_graph_sync(selected_candidate)
            print("##### >>> [DEBUG:InstructionController] Graph construction completed")
            
            # グラフを実行
            self.green_thread = eventlet.spawn(self._run_main_loop)
            
        except Exception as e:
            self.debug_print(f"Error in handle_start_instruction: {e}")
            traceback.print_exc()
