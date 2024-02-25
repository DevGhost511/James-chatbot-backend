from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from datetime import datetime
from uuid import uuid4

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, nullable = False, autoincrement = True)
    chat_id = db.Column(db.String(), nullable = True)
    name = db.Column(db.String(), nullable = False)
    email = db.Column(db.String(), unique = True, nullable = False)
    password = db.Column(db.String(), nullable = True)
    role = db.Column(db.String(), nullable = False, default = 'user')
    created_at = db.Column(db.DateTime, nullable = False,  default=datetime.utcnow)
    
    def __init__(self, name, email, password):
        self.name = name
        self.email = email
        self.password = password
    
    def register_user_if_not_exist(self):        
        db_user = User.query.filter(User.user_id == self.user_id).all()
        if not db_user:
            db.session.add(self)
            db.session.commit()
        return True
    
    def get_by_username(name):        
        db_user = User.query.filter(User.name == name).first()
        return db_user
    
    def json(self):
        return {'id': self.id, 'name':self.name}
    
    def __repr__(self):
        return f"<User {self.name}>"

class ChatId(db.Model):
    __tablename__ = 'chat_ids'

    id = db.Column(db.Integer, primary_key=True, autoincrement = True)
    chat_id = db.Column(db.String(), unique = True,  nullable = True)
    created_at = db.Column(db.DateTime, nullable = False,  default=datetime.utcnow)

    def __init__(self, chat_id):
        self.chat_id = chat_id  
    
    def json(self):
        return {'id':self.id, 'chat_id': self.chat_id, 'created_at':self.created_at}
    
    def __repr__(self):
        return f"<ChatId {self.chat_id}>"
    
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
    count = db.Column(db.Integer, nullable = False, default = 0)
    type_of_knowledge = db.Column(db.String(), nullable = False)
    created_at = db.Column(db.DateTime, nullable = False,  default=datetime.utcnow)

    def __init__(self, assistant_id, name, type_of_knowledge, count):
        self.assistant_id = assistant_id
        self.name = name
        self.type_of_knowledge = type_of_knowledge
        self.count = count

    def json(self):
        return {'id':self.id, 'assistant_id':self.assistant_id, 'name':self.name, 'type_of_knowledge':self.type_of_knowledge, 'created_at':self.created_at}
    
    def __repr__(self):
        return f"<KnowledgeBase {self.name}>"
    
class Assistant(db.Model):
    __tablename__ = 'assistants'

    id = db.Column(db.Integer, primary_key=True, autoincrement = True)
    name = db.Column(db.String(), unique = True, nullable = False)
    prompt = db.Column(db.String(), nullable = False)
    use_sql = db.Column(db.Boolean, nullable = False)
    use_pinecone = db.Column(db.Boolean, nullable = False)
    use_serp = db.Column(db.Boolean, nullable = False)
    facebook_enable = db.Column(db.Boolean, nullable = False)
    facebook_token = db.Column(db.String(), nullable = True)
    sql_host = db.Column(db.String(), nullable = True)
    sql_username = db.Column(db.String(), nullable = True)
    sql_password = db.Column(db.String(), nullable = True)
    sql_db_name = db.Column(db.String(), nullable = True)
    sql_port = db.Column(db.String(), nullable = True)
    pinecone_api_key =db.Column(db.String(), nullable = True)
    pinecone_environment = db.Column(db.String(), nullable = True)
    pinecone_index_name = db.Column(db.String(), nullable = True)
    assistant_avatar = db.Column(db.String(), nullable = True)
    user_avatar = db.Column(db.String(), nullable=True)
    weather_api = db.Column(db.Boolean, nullable = False)
    created_at = db.Column(db.DateTime, nullable = False,  default=datetime.utcnow)

    def __init__(self, name, prompt, use_serp, use_sql, use_pinecone, sql_host, sql_username, sql_password, sql_port, sql_db_name, pinecone_api_key, pinecone_environment, pinecone_index_name, facebook_enable, facebook_token, assistant_avatar, user_avatar, weather_api):
        self.name = name
        self.prompt = prompt
        self.use_sql = use_sql
        self.use_pinecone = use_pinecone
        self.use_serp = use_serp
        self.sql_host = sql_host
        self.sql_username = sql_username
        self.sql_password = sql_password
        self.sql_db_name = sql_db_name
        self.sql_port = sql_port
        self.pinecone_api_key = pinecone_api_key
        self.pinecone_environment = pinecone_environment
        self.pinecone_index_name = pinecone_index_name
        self.facebook_enable = facebook_enable
        self.facebook_token = facebook_token
        self.assistant_avatar = assistant_avatar
        self.user_avatar = user_avatar
        self.weather_api = weather_api
        
    def json(self):
        return {'id':self.id, 'assistant_name':self.name, 'prompt':self.prompt, 
                'use_sql':self.use_sql,'sql_host':self.sql_host, 'sql_username':self.sql_username, 'sql_password':self.sql_password, 'sql_port':self.sql_port, 'sql_db_name':self.sql_db_name,
                'use_pinecone':self.use_pinecone, 'pinecone_api_key':self.pinecone_api_key, 'pinecone_environment':self.pinecone_environment, 'pinecone_index_name':self.pinecone_index_name,
                'use_serp':self.use_serp,
                'facebook_enable':self.facebook_enable,
                'facebook_token':self.facebook_token,
                'created_at':self.created_at,
                'assistant_avatar':self.assistant_avatar,
                'user_avatar': self.user_avatar,
                'weather_api':self.weather_api}
    
    def __repr__(self):
        return f"<Assistant {self.name}>"
    
class ChatHistory(db.Model):
    __tablename__ = 'chat_history'

    id = db.Column(db.Integer, primary_key=True, autoincrement = True)
    chat_id = db.Column(db.String(), nullable = False)
    user_query = db.Column(db.String(), nullable = False)
    response = db.Column(db.String(), nullable = False)
    created_at = db.Column(db.DateTime, nullable = False,  default=datetime.utcnow)
    
    def __init__(self, chat_id, user_query, response):
        self.chat_id = chat_id
        self.user_query = user_query
        self.response = response

    def json(self):
        return {'id':self.id, 'chat_id':self.chat_id, 'user_query':self.user_query, 'response':self.response}
    
    def __repr__(self):
        return f"<ChatHistory {self.id}>"

class InheritChat(db.Model):
    __tablename__ = 'inherit_chat'

    id = db.Column(db.Integer, primary_key=True, autoincrement = True)
    history_id = db.Column(db.String(), nullable=False)
    user_query = db.Column(db.String(), nullable = False)
    response = db.Column(db.String(), nullable = False)
    created_at = db.Column(db.DateTime, nullable = False,  default=datetime.utcnow)

    def __init__(self, history_id, user_query, response):
        self.history_id = history_id
        self.user_query = user_query
        self.response = response

    def json(self):
        return {'id':self.id, 'history_id':self.history_id, 'user_id':self.user_query, 'response':self.response, 'count':self.count}
    
    def __repr__(self):
        return f"<InheritChat {self.id}>"   


