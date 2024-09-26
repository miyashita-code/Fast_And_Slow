import datetime
import asyncio
import uuid

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
        self.lending_ear_controller = LendingEarController(self.kg_db)
        
        # llm_clientを初期化
        self.llm_client = ChatFireworks(model="accounts/fireworks/models/llama-v3-70b-instruct", max_tokens=4096)
        
        # LinearConversationControllerにllm_clientを渡す
        self.conversation_controller = LinearConversationController(self.llm_client)
        
        # コールバック関数を設定 (修正)
        self.conversation_controller.set_callbacks(self.callback_function, self.prompt_wrapper)
    
    # 新しいラッパー関数を追加
    async def prompt_wrapper(self, prompt: str, title: str):
        # イベント名を "telluser" に変更し、データを調整
        self.send_socket_instruction("telluser", {"titles": title, "detail": prompt})
    
    def callback_function(self):
        # コールバックロジックを実装
        print("コールバックが呼び出されました。")
        # 必要に応じて他の処理を追加
        pass

    def lending_ear_run(self):
        """
        Run the backend process. Emit instructions based on message length.
        """
        print(f"run : {self.room}")
        print(f"say hello : {self.room}")
        self.socketio.emit('announce', {'announce': 'Hello, LendingEar Started!'}, room=self.room)
        self.send_socket("instruction", {"instruction" : "まずは、傾聴を始めます。初めに「状況を整理するためにいくつか質問をすること」を説明してください。この確認は省略することなく、何にもましてもっとも初めに行うことです。絶対に従ってください。\
            絶対に絶対に絶対に聞いてください。", "isLendingEar" : True})
        self.lending_ear_controller.main(self.send_socket, self.get_messages)
    
    def instruction_run(self):
        """
        Run the backend process. Emit instructions based on message length.
        """
        print(f"run : {self.room}")
        print(f"say hello : {self.room}")
        self.socketio.emit('announce', {'announce': 'Hello, LendingEar Started!'}, room=self.room)
        self.send_socket("instruction", {"instruction" : "  インストラクションを始めます。簡単なあいさつの後、iphoneのmapの使い方を説明することを共有してください。これから説明を始めることだけを伝え必要最小限にすること", "isLendingEar" : False})
        self.conversation_controller.main(self.prompt_wrapper, self.get_messages)

    def send_socket(self, event, data):
        """
        Send data to the client using a specified event.

        Args:
            event (str): Event name to emit.
            data (dict): Data to send as key-value pairs.
        """
        print("*" * 20)
        print("\n\n")
        print(f"Sending event: {event}")
        print(f"Data: {data}")
        print("*" * 20)
        print("\n\n")
        self.socketio.emit(event, data, room=self.room)
    
    def send_socket_instruction(self, event, data):
        """
        Send data to the client using a specified event.

        Args:
            event (str): Event name to emit.
            data (dict): Data to send as key-value pairs.
        """
        print("*" * 20)
        print("\n\n")
        print(f"Sending event: {event}")
        print(f"Data: {data}")
        print("*" * 20)
        print("\n\n")
        self.socketio.emit(event, data, room=self.room)

    def get_messages(self):
        """ Get the message list. """
        return self.messages

    def set_room(self, room):
        """ Set the room ID. """
        self.room = room

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
        new_message = Message(user_id=self.client_data.id, dialogue_id=self.dialogue_id, content=message_content)
        self.db.session.add(new_message)
        self.db.session.commit()
        self.messages.append(message_content)
        asyncio.run(self.lending_ear_controller.set_message(message_content))
        asyncio.run(self.conversation_controller.set_message(message_content))

    def get_recent_messages_desc(self, user_id, limit=50) -> list[str]:
        messages = Message.query.filter_by(user_id=user_id).order_by(Message.timestamp.desc()).limit(limit).all()
        return [message.content for message in messages]
    
    def get_same_context_messages_desc(self, user_id, dialogue_id, limit=50) -> list[str]:
        messages = Message.query.filter_by(user_id=user_id, dialogue_id=dialogue_id).order_by(Message.timestamp.desc()).limit(limit).all()
        return [message.content for message in messages]
    
    def stop(self):
        """ Stop the backend process. """
        self.lending_ear_controller.stop()
        self.socketio.emit('announce', {'announce': 'LendingEar Stopped!'}, room=self.room)
        disconnect(self.room)