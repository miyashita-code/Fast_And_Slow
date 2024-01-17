from flask_sqlalchemy import SQLAlchemy

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
