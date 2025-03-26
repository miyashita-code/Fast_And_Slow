import datetime
import asyncio
import uuid
import traceback
from typing import Any

from .models import Message
from planning_modules.lending_ear_modules.lend_main import LendingEarController
from planning_modules.state_machine_modules.instruction_controller import InstructionController
from planning_modules.demo_module.st import LinearConversationController
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langchain_fireworks import ChatFireworks

from flask_socketio import disconnect
from neo4j import AsyncGraphDatabase  # 同期版からAsyncGraphDatabaseに変更

from eventlet.green import threading
import eventlet

class BackEndProcess:
    """
    Class representing the backend process for handling socket connections.

    """
    DIALOGUE_ID_TIMEOUT = 3600  # 1時間をデフォルト値として設定
    
    def __init__(self, socketio, room, client_data, db, kg_db):
        """
        Initialize the backend process.

        Args:
        socketio: SocketIO instance.
        room (str): Room ID.
        client_data: Client-related data.
        db: Database instance.
        kg_db: Knowledge graph database instance.
        """
        self.socketio = socketio
        self.room = room
        self.client_data = client_data
        self.active = True
        self.is_debug = True  # デバッグモードを有効化
        self.dialogue_id = self.get_or_create_dialogue_id()
        self.db = db
        self.kg_db = kg_db
        self.lending_ear_controller = None
        self.conversation_controller = None
        self._ping_greenlet = None
        self.current_thread = None  # スレッド管理用の変数を追加
        self._current_instruction = None  # 現在のインストラクション状態を保持
        

        self.conversation_controller = InstructionController(
            send_socket=self.send_socket,
            kg_db=self.kg_db,
            is_debug=True  # デバッグフラグを渡す
        )
        
        # コールバック関数を設定
        self.conversation_controller.set_callbacks(self.callback_function)
        

        self.last_activity = datetime.datetime.utcnow()
        self.INACTIVE_TIMEOUT = 1800  # 30分のタイムアウト
        self.is_running = False
    
    def callback_function(self):
        """コールバック関数"""
        print("コールバックが呼び出されました。")
        # 必要に応じて他の処理を追加
        pass

    def update_activity(self):
        """最終アクティビティ時間を更新"""
        self.last_activity = datetime.datetime.utcnow()
    
    def is_expired(self):
        """タイムアウトしているかチェック"""
        return (datetime.datetime.utcnow() - self.last_activity).total_seconds() > self.INACTIVE_TIMEOUT

    def lending_ear_run(self):
        """傾聴モードの実行"""
        if self.is_running:
            print("Already running, reusing existing process")
            return
            
        self.is_running = True
        self.active = True
        self.update_activity()
        
        print(f"run lending ear: {self.room}")
        self.socketio.emit('announce', {'announce': 'Hello, LendingEar Started!'}, room=self.room)
     
        # コントローラーを初期化（既存のものがあれば再利用）
        if not self.lending_ear_controller:
            self.lending_ear_controller = LendingEarController(self.kg_db)
        self.conversation_controller = None
        
        self.send_socket("instruction", {
            "instruction": "まずは、傾聴を始めます。初めに「状況を整理するためにいくつか質問をすること」を説明してください。この確認は省略することなく、何にもましてもっとも初めに行うことです。絶対に従ってください。絶対に絶対に絶対に聞いてください。",
            "isLendingEar": True
        })
        
        self.lending_ear_controller.main(self.send_socket, self.get_messages)

    def instruction_run(self, selected_candidate=None):
        """
        指示モードの実行
        
        Args:
            selected_candidate (str, optional): 選択された候補の名前
        """
        if selected_candidate:
            self._current_instruction = selected_candidate
            self.debug_print(f"設定された指示: {self._current_instruction}")
            
        if self.is_running:
            self.debug_print("既存のプロセスを再利用します")
            return
            
        self.is_running = True
        self.active = True
        self.update_activity()
        
        self.debug_print(f"指示モードを開始します - Room: {self.room}")
        self.socketio.emit('announce', {'announce': 'Hello, Instruction Started!'}, room=self.room)
        self.send_socket('custom_ping', '1')
        
        if not self.conversation_controller:
            self.debug_print("新しい指示コントローラーを作成します")
            self.conversation_controller = InstructionController(
                send_socket=self.send_socket,
                kg_db=self.kg_db,
                is_debug=True
            )
            self.conversation_controller.set_callbacks(self.callback_function)
        self.lending_ear_controller = None
        
        self.debug_print("非同期タスクを開始します")
        gt = eventlet.spawn(self._run_instruction_async, self._current_instruction)
        self.debug_print("メインスレッドは継続します")
        return gt

    def _run_instruction_async(self, selected_candidate=None):
        """
        eventlet用の非同期実行関数
        
        Args:
            selected_candidate (str, optional): 選択された候補の名前
        """
        self.debug_print(f"_run_instruction_async を開始します - 選択された指示: {selected_candidate}")
        self.send_socket('custom_ping', '2')
        
        self.conversation_controller.send_socket("instruction", {
            "instruction": "インストラクションを始めます。簡単なあいさつの後、指定されたインストラクションを開始する旨を伝えてください。",
            "isLendingEar": False
        })
        self.debug_print("初期指示を送信しました")
        
        self.debug_print(f"コントローラーでメイン処理を開始します: {self.conversation_controller}")
        self.conversation_controller.main(self.get_messages)
        
        if selected_candidate:
            self.debug_print(f"選択された指示を使用します: {selected_candidate}")
            self.conversation_controller.handle_start_instruction(selected_candidate)

    def send_socket(self, event: str, data: Any):
        """Socket.IOメッセージを送信"""
        if not self.active:
            print(f"##### >>> [DEBUG:BackendProcess] Skipping socket event {event} - process not active")
            return
        
        print(f"##### >>> [DEBUG:BackendProcess] Sending socket event: {event}, data: {data}")
        try:
            # 直接emit（eventletコンテキスト内で実行されているため）
            self.socketio.emit(event, data, room=self.room)
            print(f"##### >>> [DEBUG:BackendProcess] Successfully emitted {event}")
        except Exception as e:
            print(f"##### >>> [ERROR:BackendProcess] Error in socket emission: {e}")
            traceback.print_exc()

    def get_messages(self):
        """ Get the message list. """
        return self.messages

    def set_room(self, room):
        """ルームの更新時にアクティビティも更新"""
        self.room = room
        self.update_activity()
        self.active = True  # 再アクティブ化

    def get_room(self):
        """ Get the room ID. """
        return self.room
    
    def get_or_create_dialogue_id(self):
        """ Check if the last message was sent within the timeout to detect same context or not."""
        last_message = Message.query.filter_by(user_id=self.client_data.id).order_by(Message.timestamp.desc()).first()
        if last_message and (datetime.datetime.utcnow() - last_message.timestamp).total_seconds() < self.DIALOGUE_ID_TIMEOUT:
            # Regard it as the same conversation if the last message was sent within the timeout 
            
            # Add the message to the conversation (Previous entries for the number of LIMITS, starting from the oldest to the newest)
            same_context_messages = self.get_same_context_messages_desc(self.client_data.id, last_message.dialogue_id)
            self.messages = same_context_messages[::-1]
            return last_message.dialogue_id
        else:
            return str(uuid.uuid4())

    def set_messages(self, message_content: str):
        """メッセージ設定時にアクティビティを更新"""
        self.update_activity()
        # メッセージをデータベースに保存
        new_message = Message(user_id=self.client_data.id, dialogue_id=self.dialogue_id, content=message_content)
        self.db.session.add(new_message)
        self.db.session.commit()
        self.messages.append(message_content)

        # 現在アクティブなコントローラーにのみメッセージを送信
        def process_message():
            try:
                print("Processing message...")
                if self.lending_ear_controller:
                    print("Using lending ear controller")
                    self.lending_ear_controller.set_message(message_content)
                    print("Message set, requesting next question...")
                    self.lending_ear_controller.request_next_question()
                    print("Next question requested")
                elif self.conversation_controller:
                    print("Using conversation controller")
                    self.conversation_controller.set_message(message_content)
            except Exception as e:
                print(f"Error in process_message: {e}")
                traceback.print_exc()

        # eventletを使用して非同期処理を実行
        try:
            eventlet.spawn(process_message)
        except Exception as e:
            print(f"Error processing message: {e}")

    def get_recent_messages_desc(self, user_id, limit=50) -> list[str]:
        messages = Message.query.filter_by(user_id=user_id).order_by(Message.timestamp.desc()).limit(limit).all()
        return [message.content for message in messages]
    
    def get_same_context_messages_desc(self, user_id, dialogue_id, limit=50) -> list[str]:
        messages = Message.query.filter_by(user_id=user_id, dialogue_id=dialogue_id).order_by(Message.timestamp.desc()).limit(limit).all()
        return [message.content for message in messages]
    
    def stop(self):
        """停止処理"""
        print("Pausing backend process...")
        self.is_running = False
        self.active = False
        
        if self.lending_ear_controller:
            self.lending_ear_controller.stop()
        if self.conversation_controller:
            self.conversation_controller.stop()
        
        self.socketio.emit('announce', {'announce': 'Process Paused!'}, room=self.room)

    def force_stop(self):
        """
        完全な終了処理
        """
        print("Force stopping backend process...")
        self.is_running = False
        self.active = False
        
        if self.lending_ear_controller:
            self.lending_ear_controller.stop()
            self.lending_ear_controller = None
        if self.conversation_controller:
            self.conversation_controller.stop()
            self.conversation_controller = None
            
        try:
            disconnect(self.room)
        except Exception as e:
            print(f"Error during disconnect: {e}")

    def handle_go_next_state(self):
        """go_next_stateイベントの処理"""
        print("\n##### >>> [DEBUG:BackendProcess] handle_go_next_state called")
        
        if self.conversation_controller:
            print(f"##### >>> [DEBUG:BackendProcess] Forwarding to conversation_controller: {self.conversation_controller}")
            try:
                self.conversation_controller.handle_socket_event('next_state')
                print("##### >>> [DEBUG:BackendProcess] Successfully forwarded event")
                return True
            except Exception as e:
                print(f"##### >>> [DEBUG:BackendProcess] Error forwarding event: {e}")
                traceback.print_exc()
                return False
        else:
            print("##### >>> [DEBUG:BackendProcess] No conversation_controller available!")
            return False

    def handle_go_detail(self):
        """詳細表示イベントを処理"""
        print("##### >>> [DEBUG:BackendProcess] handle_go_detail called")
        if self.conversation_controller:
            print(f"##### >>> [DEBUG:BackendProcess] Forwarding to conversation_controller: {self.conversation_controller}")
            self.conversation_controller.handle_socket_event('go_detail')

    def handle_back_to_start(self):
        """back_to_startイベントの処理"""
        print("\n##### >>> [DEBUG:BackendProcess] handle_back_to_start called")
        
        if self.conversation_controller:
            print(f"##### >>> [DEBUG:BackendProcess] Forwarding to conversation_controller: {self.conversation_controller}")
            self.conversation_controller.handle_socket_event('back_to_start')
        else:
            print("##### >>> [DEBUG:BackendProcess] No conversation_controller available!")

    def debug_print(self, msg: str):
        """デバッグメッセージを出力"""
        if self.is_debug:
            print(f"[BackEndProcess] {msg}")