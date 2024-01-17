from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_socketio import SocketIO, join_room, leave_room
from flask_cors import CORS

from flask_migrate import Migrate

import threading
import time
import jwt
import datetime
import uuid
import hashlib
import json, os
import requests
from dotenv import load_dotenv

from models import db, UserAuth

load_dotenv()



FIREBASE_API_KEY = os.environ.get('FIREBASE_API_KEY')

app = Flask(__name__)
CORS(app)


app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY_FLASK')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False



db.init_app(app)
migrate = Migrate(app, db)

socketio = SocketIO(app, cors_allowed_origins="*")

backend_instances = {}  # ルームIDをキーとするインスタンスの辞書


def sign_in_with_email_and_password(email : str, password : str, api_key=FIREBASE_API_KEY):
    url = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
    payload = {
        'email': email,
        'password': password,
        'returnSecureToken': True
    }
    response = requests.post(f"{url}?key={api_key}", data=payload)
    return response.json()




class BackEndProcess:
    def __init__(self, room, client_data):
        self.room = room
        self.messages = []
        self.active = True
        self.client_data = client_data

    def run(self):
        while self.active:
            time.sleep(5)
            message_length = sum(len(m) for m in self.messages)
            socketio.emit('message_length', {'length': message_length}, room=self.room)

    def stop(self):
        self.active = False

@app.route('/')
def index():
    return 'Hello, this is the Flask-SocketIO server!'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template("login.html",msg="")

    email = request.form['email']
    password = request.form['password']

    try:
        user = sign_in_with_email_and_password(email, password)
        session['usr'] = email
        return redirect(url_for('create_user'))
    except Exception as e:
        return render_template("login.html", msg="メールアドレスまたはパスワードが間違っています。")


@app.route("/create_user", methods=['GET'])
def create_user():
    usr = session.get('usr')
    if usr == None:
        return redirect(url_for('login'))
    return render_template("create_user.html", usr=usr)

@app.route('/register', methods=['POST'])
def register_user():
    usr = session.get('usr')
    if usr == None:
        return redirect(url_for('login'))

    name = request.form.get('username')
    user_id = str(uuid.uuid4())
    api_key = hashlib.sha256(name.encode()).hexdigest()

    new_user = UserAuth(id=user_id, name=name, api_key=api_key)
    db.session.add(new_user)
    db.session.commit()

    return render_template("display_api_key.html", api_key=api_key, name=name, user_id=user_id)


@app.route('/logout')
def logout():
    del session['usr']
    return redirect(url_for('login'))

@app.route('/api/token', methods=['POST'])
def get_token():
    print("api auth tryal")
    api_key = request.headers.get('API-Key')
    user = UserAuth.query.filter_by(api_key=api_key).first()

    if user:
        payload = {
            'user_id': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }
        token = jwt.encode(payload, os.environ.get('SECRET_KEY_JWT'), algorithm='HS256')
        return jsonify({'token': token})
    else:
        return jsonify({'message': 'Invalid API Key'}), 401


@socketio.on('connect')
def handle_connect():
    token = request.args.get('token')
    data = None
    current_user = None
    

    if not token:
        return jsonify({'message': 'Token is missing!'}), 403

    try:
        data = jwt.decode(token, os.environ.get('SECRET_KEY_JWT'), algorithms=['HS256'])
        current_user = UserAuth.query.filter_by(id=data['user_id']).first()
    except:
        return jsonify({'message': 'Token is invalid!'}), 403

    client_data = {
        'id': data['user_id'],
        'name': current_user,
    }

    print(f"socket connected : {current_user}")

    room = request.sid
    join_room(room)
    bp = BackEndProcess(room, client_data)
    backend_instances[room] = bp
    threading.Thread(target=bp.run).start()

@socketio.on('disconnect')
def handle_disconnect():
    room = request.sid
    leave_room(room)
    if room in backend_instances:
        backend_instances[room].stop()
        del backend_instances[room]


@socketio.on('message')
def handle_message(data):
    room = request.sid
    if room in backend_instances:
        backend_instances[room].messages.append(data['message'])

if __name__ == '__main__':
    socketio.run(app, debug=True, port=int(os.environ.get('PORT')))
