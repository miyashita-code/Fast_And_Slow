import datetime
import asyncio
import uuid
import traceback

from .models import Message
from lending_ear_modules import LendingEarController
from demo_module.st import LinearConversationController
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langchain_fireworks import ChatFireworks

from flask_socketio import disconnect

class BackEndProcess:
    """
    Class representing the backend process for handling socket connections.

    """
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
        self.room = room
        self.messages = []
        self.active = True
        self.client_data = client_data
        self.socketio = socketio
        self.DIALOUGE_ID_TIMEOUT = 300 #(sec)
        self.dialogue_id = self.get_or_create_dialogue_id()
        self.db = db
        self.kg_db = kg_db
        self.lending_ear_controller = None
        self.conversation_controller = None
        self.current_thread = None  # スレッド管理用の変数を追加
        
        # llm_clientを初期化
        self.llm_client = ChatFireworks(model="accounts/fireworks/models/llama-v3p1-70b-instruct", max_tokens=4096)
        
        # LinearConversationControllerにllm_clientを渡す
        self.conversation_controller = LinearConversationController(self.llm_client)
        
        # コールバック関数を設定 (修正)
        self.conversation_controller.set_callbacks(self.callback_function, self.prompt_wrapper)
        
        self.last_activity = datetime.datetime.utcnow()
        self.INACTIVE_TIMEOUT = 1800  # 30分のタイムアウト
        self.is_running = False
    
    # 新しいラッパー関数を追加
    async def prompt_wrapper(self, prompt: str, title: str):
        # イベント名を "telluser" に変更し、データを調整
        self.send_socket_instruction("telluser", {"titles": title, "detail": prompt})
    
    def callback_function(self):
        # コールバックロジックを実装
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

    def instruction_run(self):
        """指示モードの実行"""
        if self.is_running:
            print("Already running, reusing existing process")
            return
            
        self.is_running = True
        self.active = True
        self.update_activity()
        
        print(f"run instruction: {self.room}")
        self.socketio.emit('announce', {'announce': 'Hello, Instruction Started!'}, room=self.room)
        
        # コントローラーを初期化（既存のものがあれば再利用）
        if not self.conversation_controller:
            self.conversation_controller = LinearConversationController(self.llm_client)
            self.conversation_controller.set_callbacks(self.callback_function, self.prompt_wrapper)
        self.lending_ear_controller = None
        
        self.send_socket("instruction", {
            "instruction": "インストラクションを始めます。簡単なあいさつの後、是非散歩に行きましょう。そのための身支度をする旨を伝えてください。",
            "isLendingEar": False
        })
        
        self.conversation_controller.main(self.prompt_wrapper, self.get_messages)

    def send_socket(self, event, data):
        """
        Send data to the client using a specified event.

        Args:
            event (str): Event name to emit.
            data (dict): Data to send as key-value pairs.
        """

        self.socketio.emit(event, data, room=self.room)
    
    def send_socket_instruction(self, event, data):
        """
        Send data to the client using a specified event.

        Args:
            event (str): Event name to emit.
            data (dict): Data to send as key-value pairs.
        """
        self.socketio.emit(event, data, room=self.room)

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
        if last_message and (datetime.datetime.utcnow() - last_message.timestamp).total_seconds() < self.DIALOUGE_ID_TIMEOUT:
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
        async def process_message():
            try:
                print("Processing message...")
                if self.lending_ear_controller:
                    print("Using lending ear controller")
                    await self.lending_ear_controller.set_message(message_content)
                    print("Message set, requesting next question...")
                    await self.lending_ear_controller.request_next_question()
                    print("Next question requested")
                elif self.conversation_controller:
                    print("Using conversation controller")
                    await self.conversation_controller.set_message(message_content)
            except Exception as e:
                print(f"Error in process_message: {e}")
                traceback.print_exc()

        # 新しいイベントループを作成して非同期処理を実行
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(process_message())
            loop.close()
        except Exception as e:
            print(f"Error processing message: {e}")

    def get_recent_messages_desc(self, user_id, limit=50) -> list[str]:
        messages = Message.query.filter_by(user_id=user_id).order_by(Message.timestamp.desc()).limit(limit).all()
        return [message.content for message in messages]
    
    def get_same_context_messages_desc(self, user_id, dialogue_id, limit=50) -> list[str]:
        messages = Message.query.filter_by(user_id=user_id, dialogue_id=dialogue_id).order_by(Message.timestamp.desc()).limit(limit).all()
        return [message.content for message in messages]
    
    def stop(self):
        """
        一時停止処理（完全な終了ではない）
        """
        print("Pausing backend process...")
        self.is_running = False
        self.active = False
        
        # コントローラーは維持したまま一時停止
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
        """
        'go_next_state' イベントを処理し、次のステートへ進みます。
        """
        if self.conversation_controller:
            self.conversation_controller.handle_socket_event('next_state')

    def handle_go_detail(self):
        """
        'go_detail' イベントを処理し、詳細状態へ遷移します。
        """
        if self.conversation_controller:
            self.conversation_controller.handle_socket_event('go_detail')

    def handle_back_to_start(self):
        """
        'back_to_start' イベントを処理し、最初の状態に戻ります。
        """
        if self.conversation_controller:
            self.conversation_controller.handle_socket_event('back_to_start')
