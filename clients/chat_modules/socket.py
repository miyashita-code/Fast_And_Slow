import os
import requests
import socketio
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()



# APIキーとURLをenvファイルから取得
API_KEY = os.getenv('OWN_API_KEY')
URL =  os.getenv('SERVER_URL')

# トークンを取得する関数
def get_token():
    try:
        response = requests.post(f'{URL}/api/token', headers={'API-Key': API_KEY})
        return response.json()['token']
    except requests.RequestException as e:
        print(f'Error fetching token: {e}')
        return None

# Socket.IOサーバーに接続する関数
def init_socket_connection():
    token = get_token()
    if token:
        sio = socketio.Client()
        sio.connect(URL, headers={'token': token})

        @sio.event
        def connect():
            print('Connected to the server')


        @sio.event
        def disconnect():
            print('Disconnected from the server')

        # メッセージ送信のための関数（必要に応じてカスタマイズ）
        def send_message(message):
            sio.emit('message', {'message': message})

        # メッセージ送信の例
        send_message('Hello, world!')
    else:
        print('Token fetch failed')

# Socket.IO接続の初期化
init_socket_connection()
