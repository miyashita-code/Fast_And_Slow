import os
import requests
import socketio
from dotenv import load_dotenv

# Load the .env file to access environment variables
load_dotenv()

class SocketClient:
    def __init__(self):
        # Retrieve API key and URL from environment variables
        self.api_key = os.getenv('OWN_API_KEY')
        self.url = os.getenv('SERVER_URL')
        self.sio = socketio.Client()
        self.configure_events()

    def __get_token(self):
        # Function to get a token from the server
        try:
            response = requests.post(f'{self.url}/api/token', headers={'API-Key': self.api_key})
            return response.json()['token']
        except requests.RequestException as e:
            # Print error message if token fetch fails
            print(f'Error fetching token: {e}')
            return None

    def configure_events(self):
        # Configure Socket.IO events

        @self.sio.event
        def connect():
            # Event triggered when connected to the server
            print('Connected to the server')

        @self.sio.event
        def disconnect():
            # Event triggered when disconnected from the server
            print('Disconnected from the server')

    def connect(self):
        # Function to connect to the Socket.IO server
        token = self.__get_token()
        if token:
            self.sio.connect(self.url, headers={'token': token})
        else:
            # Print message if token fetch fails
            print('Token fetch failed')

    def send_message(self, message):
        # Function to send a message to the server
        self.sio.emit('message', {'message': message})

    def disconnect(self):
        # Function to disconnect from the Socket.IO server
        self.sio.disconnect()

