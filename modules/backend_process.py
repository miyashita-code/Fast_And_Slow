import datetime
import uuid

from .models import Message
from autogpt_modules.core.auto_gpt import autogpt_main
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage


class BackEndProcess:
    """
    Class representing the backend process for handling socket connections.

    """
    def __init__(self, socketio, room, client_data, db):
        """
        Initialize the backend process.

        Args:
        socketio: SocketIO instance.
        room (str): Room ID.
        client_data: Client-related data.
        """
        self.room = room
        self.messages = []
        self.active = True
        self.client_data = client_data
        self.socketio = socketio
        self.DIALOUGE_ID_TIMEOUT = 300 #(sec)
        self.dialogue_id = self.get_or_create_dialogue_id()
        self.db = db
        self.isFin = False
        


    def run(self):
        """
        Run the backend process. Emit instructions based on message length.
        """
        print(f"run : {self.room}")
        print(f"say hello : {self.room}")
        self.socketio.emit('announce', {'announce': 'Hello, autoGpt Started!'}, room=self.room)

        self.send_socket("instruction", "まずは、傾聴を心がけてください。ユーザーの状態を把握することが第一の目標です。虚偽の事実を伝えないように十分に注意してください。")
        self.isFin = False
        autogpt_main(self.send_socket, self.get_messages, self.isFin)



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

    def set_messages(self, message_content : str):
        new_message = Message(user_id=self.client_data.id, dialogue_id=self.dialogue_id, content=message_content)
        self.db.session.add(new_message)
        self.db.session.commit()
        self.messages.append(message_content)

    def get_recent_messages_desc(self, user_id, limit=50) -> list[str]:
        messages = Message.query.filter_by(user_id=user_id).order_by(Message.timestamp.desc()).limit(limit).all()
        return [message.content for message in messages]
    
    def get_same_context_messages_desc(self, user_id, dialogue_id, limit=50) -> list[str]:
        messages = Message.query.filter_by(user_id=user_id, dialogue_id=dialogue_id).order_by(Message.timestamp.desc()).limit(limit).all()
        return [message.content for message in messages]
    
    def stop(self):
        """ Stop the backend process. """
        isFin = True
        self.socketio.emit('announce', {'announce': 'autoGpt Stopped!'}, room=self.room)
        self.socketio.disconnect(self.room)
