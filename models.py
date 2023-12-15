from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from datetime import datetime
from uuid import uuid4

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, nullable = False, autoincrement = True)
    username = db.Column(db.String(), unique = True, nullable = False)
    password = db.Column(db.String(), unique = True, nullable = False)
    created_at = db.Column(db.DateTime, nullable = False,  default=datetime.utcnow)
    role = db.Column(db.String(), default="owner") 

    __table_args__ = (
        db.CheckConstraint(role.in_(['owner', 'member', 'user']), name='role_types'),      
    )

    def __init__(self, username, password, created_at, role):
        self.username = username        
        self.password = password        
        self.created_at = created_at        
        self.role = role
    
    def register_user_if_not_exist(self):        
        db_user = User.query.filter(User.username == self.username).all()
        if not db_user:
            db.session.add(self)
            db.session.commit()
        
        return True
    
    def get_by_username(username):        
        db_user = User.query.filter(User.username == username).first()
        return db_user
    
    def json(self):
        return {'id': self.id, 'username':self.username}
    
    def __repr__(self):
        return f"<User {self.username}>"
    
class PrePrompt(db.Model):
    __tablename__ = 'preprompts'

    id = db.Column(db.Integer, primary_key=True, autoincrement = True)
    title = db.Column(db.String(), unique = True, nullable = False)
    prompt = db.Column(db.String(), nullable = False)
    created_at = db.Column(db.DateTime, nullable = False,  default=datetime.utcnow)
    assistant_id = db.Column(db.Integer)

    def __init__(self, assistant_id, title, prompt):
        self.assistant_id = assistant_id
        self.title = title        
        self.prompt = prompt      
    
    def json(self):
        return {'id':self.id,'assistant_id':self.assistant_id, 'title':self.title, 'prompt':self.prompt, 'created_at':self.created_at}
    
    def __repr__(self):
        return f"<PrePrompt {self.title}>"
    
class CloserPrompt(db.Model):
    __tablename__ = 'closer_prompts'

    id = db.Column(db.Integer, primary_key=True, autoincrement = True)
    prompt = db.Column(db.String(), nullable = False)
    created_at = db.Column(db.DateTime, nullable = False,  default=datetime.utcnow)
    assistant_id = db.Column(db.Integer)

    def __init__(self, assistant_id, prompt):
        self.assistant_id = assistant_id
        self.prompt = prompt  

    def json(self):
        return {'id':self.id, 'assistant_id':self.assistant_id, 'prompt':self.prompt, 'created_at':self.created_at}
    
    def __repr__(self):
        return f"<CloserPrompt {self.prompt}>"
    
class PushPrompt(db.Model):
    __tablename__ = 'push_prompts'

    id = db.Column(db.Integer, primary_key=True, autoincrement = True)
    prompt = db.Column(db.String(), nullable = False)
    created_at = db.Column(db.DateTime, nullable = False,  default=datetime.utcnow)
    assistant_id = db.Column(db.Integer)

    def __init__(self, assistant_id, prompt):
        self.assistant_id = assistant_id
        self.prompt = prompt    

    def json(self):
        return {'id':self.id, 'assistant_id':self.assistant_id, 'prompt':self.prompt, 'created_at':self.created_at}
    
    def __repr__(self):
        return f"<PushPrompt {self.prompt}>"
    
class KnowledgeBase(db.Model):
    __tablename__ = 'knowledge_bases'

    id = db.Column(db.Integer, primary_key=True, autoincrement = True)
    assistant_id = db.Column(db.String(), nullable = False)
    name = db.Column(db.String(), unique = True, nullable = False)
    type_of_knowledge = db.Column(db.String(), nullable = False)
    created_at = db.Column(db.DateTime, nullable = False,  default=datetime.utcnow)

    def __init__(self, assistant_id, name, type_of_knowledge):
        self.assistant_id = assistant_id
        self.name = name
        self.type_of_knowledge = type_of_knowledge    

    def json(self):
        return {'id':self.id, 'assistant_id':self.assistant_id, 'name':self.name, 'type_of_knowledge':self.type_of_knowledge, 'created_at':self.created_at}
    
    def __repr__(self):
        return f"<KnowledgeBase {self.name}>"
    
class Assistant(db.Model):
    __tablename__ = 'assistants'

    id = db.Column(db.Integer, primary_key=True, autoincrement = True)
    name = db.Column(db.String(), unique = True, nullable = False)
    created_at = db.Column(db.DateTime, nullable = False,  default=datetime.utcnow)

    def __init__(self, name):
        self.name = name

    def json(self):
        return {'id':self.id, 'assistant_name':self.name, 'created_at':self.created_at}
    
    def __repr__(self):
        return f"<Assistant {self.name}>"
    
class ChatHistory(db.Model):
    __tablename__ = 'chat_history'

    id = db.Column(db.Integer, primary_key=True, autoincrement = True)
    user_id = db.Column(db.Integer, nullable = False)
    user_query = db.Column(db.String(), nullable = False)
    response = db.Column(db.String(), nullable = False)
    created_at = db.Column(db.DateTime, nullable = False,  default=datetime.utcnow)

    def __init__(self, user_id, user_query, response):
        self.user_id = user_id
        self.user_query = user_query
        self.response = response

    def json(self):
        return {'id':self.id, 'user_id':self.user_id, 'user_query':self.user_query, 'response':self.response}
    
    def pre_json(self):
        return [
            {'id':self.id, 'user_id':self.user_id, 'sender':'you', 'message':self.user_query},
            {'id':self.id, 'user_id':self.id, 'sender':'bot', 'message':self.response}
        ]
    
    def __repr__(self):
        return f"<ChatHistory {self.id}>"


class InheritChat(db.Model):
    __tablename__ = 'inherit_chat'

    id = db.Column(db.Integer, primary_key=True, autoincrement = True)
    user_id = db.Column(db.Integer, nullable = False)
    inherit_user = db.Column(db.Integer, nullable = False)
    count = db.Column(db.Integer, nullable = False)
    created_at = db.Column(db.DateTime, nullable = False,  default=datetime.utcnow)

    def __init__(self, user_id, inherit_user, count):
        self.user_id = user_id
        self.inherit_user = inherit_user
        self.count = count

    def json(self):
        return {'id':self.id, 'user_id':self.user_id, 'inherit_user':self.inherit_user, 'count':self.count}
    
    def __repr__(self):
        return f"<InheritChat {self.id}>"   

    
