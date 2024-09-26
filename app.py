from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_socketio import SocketIO, join_room, leave_room
from flask_cors import CORS
from flask_migrate import Migrate

import threading
import requests
import jwt
import datetime
import uuid
import hashlib
import os
import json
import requests
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials, messaging


from modules import db, UserAuth, BackEndProcess, parse_to_langchain_message_str
from neo4j_modules.care_kg_db import CareKgDB
# Load environment variables
load_dotenv()

# Firebase API key for authentication
FIREBASE_API_KEY = os.environ.get('FIREBASE_API_KEY')
firebase_credentials = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
cred = credentials.Certificate(firebase_credentials)
firebase_admin.initialize_app(cred)

# Initialize Flask application
app = Flask(__name__)
CORS(app)

# Get DATABASE_URL from Heroku's environment variables
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

# If the URL starts with 'postgres://', replace it with 'postgresql://'
# This is necessary because SQLAlchemy doesn't accept 'postgres://' scheme
if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)

# Update SQLAlchemy configuration with the corrected DATABASE_URL
# Configure Flask app with environment variables
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY_FLASK')
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database and migration
db.init_app(app)
migrate = Migrate(app, db)

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Dictionary to store backend instances keyed by room ID
backend_instances = {}

def sign_in_with_email_and_password(email: str, password: str, api_key=FIREBASE_API_KEY):
    """
    Authenticate user with email and password using Firebase.

    Args:
    email (str): User's email.
    password (str): User's password.
    api_key (str): Firebase API key.

    Returns:
    dict: Response from Firebase authentication.
    error_message (str): Error message if authentication fails.
    """
    url = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
    payload = {
        'email': email,
        'password': password,
        'returnSecureToken': True
    }

    error_message = "通信エラーが発生しました。"
    
    try:
        response = requests.post(f"{url}?key={api_key}", data=payload)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.HTTPError as errh:
        error_message = "メールアドレスまたはパスワードが間違っています。"
    except requests.exceptions.ConnectionError as errc:
        pass
    except requests.exceptions.Timeout as errt:
        pass
    except requests.exceptions.RequestException as err:
        pass
    return None, error_message


def check_token(token):
    """
    Check if the JWT token is valid.

    Args:
    token (str): JWT token.

    Returns:
    tuple: (is_valid (bool), current_user (UserAuth), error_message (str))
    """
    current_user = None

    if not token:
        return (False, None, 'Token is missing!')

    try:
        data = jwt.decode(token, os.environ.get('SECRET_KEY_JWT'), algorithms=['HS256'])
        current_user = UserAuth.query.filter_by(id=data['user_id']).first()
    except:
        return (False, None, 'Token is invalid!')

    print(f"current user : {current_user}, is : {current_user.id}")
    return (True, current_user, None)

@app.route('/')
def index():
    """ Return the welcome message. """
    return 'Hello, this is the Flask-SocketIO server!'

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle the login process. Show login page on GET request, 
    and handle login logic on POST request.
    """
    if request.method == 'GET':
        return render_template("login.html", msg="")

    email = request.form['email']
    password = request.form['password']


    user, error_message = sign_in_with_email_and_password(email, password)

    if user is None:
        return render_template("login.html", msg=error_message)

    session['usr'] = email
    return redirect(url_for('create_user'))

@app.route("/create_user", methods=['GET'])
def create_user():
    """
    Show the create user page. Redirect to login if the user is not in session.
    """
    usr = session.get('usr')

    if usr is None:
        return redirect(url_for('login'))

    return render_template("create_user.html", usr=usr)

@app.route('/fcm/console', methods=['GET', 'POST'])
def fcm_console():
    usr = session.get('usr')
    if usr is None:
        return redirect(url_for('login'))
    
    # user_authテーブルからfcm_tokenの一覧を取得
    users = UserAuth.query.filter(UserAuth.fcm_token != None).all()
    token_list = [user.fcm_token for user in users]
    
    message_sent = False
    success = False
    response_msg = ""
    sent_json = ""
    
    if request.method == 'POST':
        registration_token = request.form.get('registration_token')
        notifyDisplayInfo = request.form.get('notifyDisplayInfo')
        notifyDetail = request.form.get('notifyDetail')
        notifySpeechReading = request.form.get('notifySpeechReading')

        message_data = {
            'data': {
                'notifyDisplayInfo': notifyDisplayInfo,
                'notifyDetail': notifyDetail,
                'notifySpeechReading': notifySpeechReading
            },
            'android': messaging.AndroidConfig(priority='high')
        }

        if request.form.get('send_to_all') == 'on':
            message_data['topic'] = 'all'
        else:
            message_data['token'] = registration_token

        try:
            response = messaging.send(messaging.Message(**message_data))
            message_sent = True
            success = True
            response_msg = f'Successfully sent message: {response}'

            def serialize_message_data(data):
                serialized_data = {}
                for key, value in data.items():
                    if isinstance(value, messaging.AndroidConfig):
                        serialized_data[key] = {'priority': value.priority}
                    else:
                        serialized_data[key] = value
                return serialized_data

            sent_json = json.dumps(serialize_message_data(message_data), indent=4)
        except Exception as e:
            message_sent = True
            success = False
            response_msg = f'Failed to send message: {e}'
    
    return render_template("fcm_console.html", usr=usr, message_sent=message_sent, success=success,
                           response_msg=response_msg, sent_json=sent_json, token_list=token_list)
@app.route('/register', methods=['POST'])
def register_user():
    """
    Handle user registration. Create new user and store in database.
    """
    usr = session.get('usr')
    if usr is None:
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
    """ Handle user logout. Clear session and redirect to login. """
    session.pop('usr', None)
    return redirect(url_for('login'))

@app.route('/api/token', methods=['POST'])
def get_token():
    """
    Generate and return a JWT token for authenticated users.
    """
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
    
@app.route('/api/fcm/token_register', methods=['POST'])
def register_fcm_token():
    """
    Register FCM token for push notifications.
    """
    api_key = request.headers.get('API-Key')
    fcm_token = request.headers.get('FCM-Token')

    # Get user by API key
    user = UserAuth.query.filter_by(api_key=api_key).first()

    if not user:
        return jsonify({'message': 'Invalid API Key'}), 401

    # Update FCM token
    user.fcm_token = fcm_token
    db.session.commit()

    return jsonify({'message': 'FCM token registered successfully!'})
    
@app.route('/get_reminders', methods=['GET'])
def get_reminders():


    return jsonify([{"time": 1708595280, "tellmessage": "テスト", "detail": "開発テスト用です"}])

@socketio.on('connect')
def handle_connect(auth=None):
    """
    Handle socket connection. Join room and create/update backend process instance.
    """
    print(f"handshake tryal : {auth}")
    token = request.headers.get('token')
    way = request.headers.get('way')

    if not token:
        token = request.args.get('token')
    if not way:
        way = request.args.get('way')

    is_valid, current_user, error_message = check_token(token)

    if not is_valid:
        print("valid handshake")
        return jsonify({'message': error_message}), 403

    print(f"socket connected : {current_user.name}")

    # join room
    room = request.sid
    join_room(room)

    # demo 
    way = "instruction"
    
    # Initialize the knowledge graph database
    kg_db = CareKgDB(uri=os.environ.get('NEO4J_URI'), user=os.environ.get('NEO4J_USERNAME'), password=os.environ.get('NEO4J_PASSWORD'), user_uuid=current_user.id)

    # Manage backend process instance for the connected user
    if current_user.id not in backend_instances:
        bp = BackEndProcess(socketio, room, current_user, db, kg_db)
        backend_instances[current_user.id] = bp
        if way == "instruction":
            threading.Thread(target=bp.instruction_run).start()
        else:
            threading.Thread(target=bp.lending_ear_run).start()
    else:
        backend_instances[current_user.id].set_room(room)


@socketio.on('disconnect')
def handle_disconnect():
    """
    Handle socket disconnection.
    Leave room and stop backend process.
    """
    token = request.headers.get('token')
    if not token:
        token = request.args.get('token')

    is_valid, current_user, error_message = check_token(token)
    if not is_valid:
        print("Invalid token during disconnect")
        return

    print(f"Socket disconnected: {current_user.name}")

    # Leave room
    room = request.sid
    leave_room(room)

    # Stop and remove backend process instance for the disconnected user
    if current_user.id in backend_instances:
        bp = backend_instances[current_user.id]
        if bp.get_room() == room:
            bp.stop()
            del backend_instances[current_user.id]

@socketio.on('chat_message')
def handle_message(data):
    """
    Handle chat messages. Validate token and process message.
    """
    # get token from headers or query parameters
    token = request.args.get('token')

    is_valid, current_user, error_message = check_token(token)
    
    if not is_valid:
        return jsonify({'message': error_message}), 403

    print(f"chat message come")
    if current_user is None:
        print("current_user is None")
        return jsonify({'message': 'User not found!'}), 404

    if current_user.id in backend_instances:
        print(f"message received : {data}, room : {request.sid}, bg : {backend_instances}")
        try:
            message_content = parse_to_langchain_message_str(data)
            backend_instances[current_user.id].set_messages(message_content)
        except ValueError as e:
            print(f"Error: {str(e)}")
            return jsonify({'message': 'Invalid message format!'}), 400

if __name__ == '__main__':
    socketio.run(app, debug=True, host="localhost", port=int(os.environ.get('PORT')))
