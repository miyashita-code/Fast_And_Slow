from flask_sqlalchemy import SQLAlchemy
import datetime
import uuid

db = SQLAlchemy()


db = SQLAlchemy()

class UserAuth(db.Model):
    __tablename__ = 'user_auth'

    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    api_key = db.Column(db.String, nullable=False)

    def __init__(self, id, name, api_key):
        self.id = id
        self.name = name
        self.api_key = api_key

    def __repr__(self):
        return f"<UserAuth {self.name}>"



class Message(db.Model):
    __tablename__ = 'message'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('user_auth.id'), nullable=False)
    dialogue_id = db.Column(db.String, nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __init__(self, user_id, dialogue_id, content):
        self.user_id = user_id
        self.dialogue_id = dialogue_id
        self.content = content

    def __repr__(self):
        return f"<Message {self.content}>"


