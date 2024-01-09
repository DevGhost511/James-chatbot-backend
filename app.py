import os
import uuid
import time
from dotenv import load_dotenv
from flask import Flask, request, jsonify, make_response
from sqlalchemy import func, desc
from flask_cors import CORS
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from utils import generate_kb_from_file, generate_kb_from_url, get_response
from models import db, ChatId, User, PushPrompt, PrePrompt, CloserPrompt, KnowledgeBase, Assistant, ChatHistory, InheritChat
from vectorizor import generate_final_answer,pinecone_result, sql_result, serp_result, simple_generate, del_knowledge_by_knowledge_id, del_knowledgebase_by_assistant_id, del_all_records, preprompt_generate, query_with_dolt, sql_connect, pinecone_connect, query_with_both

app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db?check_same_thread=False&mode=WAL'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_POOL_SIZE'] = 20
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER')

db.init_app(app)
migrate = Migrate(app, db)
CORS(app)

@app.route("/")
def index():
   db.create_all()
   # del_all_records()
   # print('Deleted')
   return "This is APIs for CustomGPT!"

# User register
@app.route('/register', methods =['POST'])
def register():
   try:
      data = request.get_json()
      print(data)
      name = data['name']
      email = data['email']
      password = data['password']
      new_user = User(name=name, email=email, password=password)
      db.session.add(new_user)
      db.session.commit()
      return make_response(jsonify({'result':new_user.id}), 201)
   except Exception as e:
      print(str(e))
      return make_response(jsonify({'result':'User already exists'}), 409)

#  User log in
@app.route('/login', methods=['POST'])
def login():
   try:
      data = request.get_json()
      email = data['email']
      password = data['password']
      user = User.query.filter_by(email=email).first()
      if user:
         if user.password == password:
            return make_response(jsonify({'result':user.id}), 200)
         else:
            return make_response(jsonify({'result':'Incorrect password'}), 400)
      else:
         return make_response(jsonify({'result':'User does not exist'}), 400)
   except Exception as e:
      print(str(e))
      return make_response(jsonify({'result':'Error'}), 400)
            
#  Google auth
@app.route('/google_auth', methods=['POST'])
def google_auth():
   try:
      data = request.get_json()
      email = data['email']
      name = data['name']
      if 'password' in data:
         password = data['password']
      else:
         password = ''
      user = User.query.filter_by(email=email).first()
      if user:
         return make_response(jsonify({'result':user.id}), 201)
      new_user = User(email=email, name=name, password=password)
      db.session.add(new_user)
      db.session.commit()
      return make_response(jsonify({'result':new_user.id}), 201)
   except Exception as e:
      print(str(e))
      return make_response(jsonify({'result':'Error'}), 400)

@app.route('/test_serp', methods=['POST'])
def test_serp():
   data = request.get_json()
   query = data['query']
   result = serp_result(query)
   print('Result >>', result)
   return make_response(jsonify({'result':result}))

@app.route('/test_sql', methods =['POST'])
def test_sql():
   data = request.get_json()
   assistant_id = data['assistant_id']
   query = data['query']
   result = sql_result(assistant_id=assistant_id, query=query)
   print('Result >>>', result)
   return make_response(jsonify({'result':result}))

@app.route('/test_pinecone', methods =['POST'])
def test_pinecone():
   data = request.get_json()
   assistant_id = data['assistant_id']
   query = data['query']
   result = pinecone_result(assistant_id=assistant_id, query=query)
   print('Result >>>', result)
   return make_response(jsonify({'result':result}))

@app.route('/user_query', methods=['POST'])
def test_final():
   try:
      start_time = time.time()
      data = request.get_json()
      query = data['query']
      print(data)
      chat_id = data['chat_id']
      if 'assistant_id' in data:
         assistant_id = data['assistant_id']
      else :
         assistant_id = 1
      if chat_id == '': # New user
         chat_id = str(uuid.uuid4())
         print(chat_id)
         chat = ChatId(chat_id=chat_id)
         db.session.add(chat)
         db.session.commit()
      # Get 3 recent chat history
      chat_history = ChatHistory.query.filter_by(chat_id=chat_id).order_by(desc(ChatHistory.created_at)).limit(3).all()
      latest_records = [chat.json() for chat in chat_history]   
      
      response = generate_final_answer(assistant_id=assistant_id, query=query)

      closer_prompt = CloserPrompt.query.order_by(func.random()).first()
         
      pre_prompts= preprompt_generate(query)
      pre_prompts = pre_prompts.replace('1. ', '').replace('2. ', '').replace('3. ', '').replace('. ', '.').replace('"','')
      pre_prompts = pre_prompts.split('\n')
      new_chat = ChatHistory(chat_id=chat_id, user_query=query, response=response)
      #  Save messages to database  
      db.session.add(new_chat)
      db.session.commit()
      end_time = time.time()
      print(response)
      print(f"The query took {end_time-start_time} seconds")

      return make_response(jsonify({'response':response, 'closer':closer_prompt.prompt, 'pre_prompts':pre_prompts, 'chat_id':new_chat.chat_id}), 201)

   except Exception as e:
      print(str(e))
      response = 'Busy network. Try again later'
      return make_response(jsonify({'response':response}), 201)

def query_from_sql(data):
   try:
      start_time = time.time()
      # print(data)
      query = data['query']
      if 'user_id' in data:
         user_id = data['user_id']
      else:
         user_id = 1
      if 'assistant_id' in data:
         assistant_id = data['assistant_id']
      else :
         assistant_id = 1
      if user_id == '': # New user
         user_id = str(uuid.uuid4())
         user = User(user_id=user_id)
         db.session.add(user)
         db.session.commit()
      
      prompt = Assistant.query.filter_by(assistant_id=assistant_id).first().prompt
      # print(f"Prompt of Assistant >>> {prompt}")
      # Get 3 recent chat history
      chat_history = ChatHistory.query.order_by(desc(ChatHistory.created_at)).limit(3).all()
      latest_records = [chat.json() for chat in chat_history]
      # print(latest_records)
      # return latest_records
      response = get_response(query, prompt, latest_records, user_id, assistant_id)
      closer_prompt = CloserPrompt.query.order_by(func.random()).first()
      
      pre_prompts= preprompt_generate(query)
      pre_prompts = pre_prompts.replace('1. ', '').replace('2. ', '').replace('3. ', '').replace('. ', '.').replace('"','')
      pre_prompts = pre_prompts.split('\n')
      new_chat = ChatHistory(user_id=user_id, user_query=query, response=response)
      #  Save messages to database  
      db.session.add(new_chat)
      db.session.commit()
      end_time = time.time()
      print(f"The query took {end_time-start_time} seconds")
      return make_response(jsonify({'response':response, 'closer':closer_prompt.prompt, 'pre_prompts':pre_prompts, 'chat_id':new_chat.id}), 201)

   except Exception as e:
      print(str(e))
      response = 'Busy network. Try again later'
      return make_response(jsonify({'response':response}), 201)

# Response to the query
@app.route('/user_query1', methods=['POST'])
def query():
   try:
      data = request.get_json()
      print(data)
      query = data['query']
      if 'user_id' in data:
         user_id = data['user_id']
      else:
         user_id = 1
      if 'assistant_id' in data:
         assistant_id = data['assistant_id']
      else :
         assistant_id = 1
      prompt = Assistant.query.filter_by(user_id=user_id).first().prompt

      chat_history = ChatHistory.query.order_by(desc(ChatHistory.created_at)).limit(6).all()
      latest_records = [chat.json() for chat in chat_history]
      # print(latest_records)
      # return latest_records
      response = get_response(query, prompt, latest_records, user_id, assistant_id)
      closer_prompt = CloserPrompt.query.order_by(func.random()).first()
      
      pre_prompts= preprompt_generate(query)
      pre_prompts = pre_prompts.replace('1. ', '').replace('2. ', '').replace('3. ', '').replace('. ', '.').replace('"','')
      pre_prompts = pre_prompts.split('\n')
      new_chat = ChatHistory(user_id=user_id, user_query=query, response=response)
      #  Save messages to database  
      db.session.add(new_chat)
      db.session.commit()
      # print(response)
      return make_response(jsonify({'response':response, 'closer':closer_prompt.prompt, 'pre_prompts':pre_prompts, 'chat_id':new_chat.id}), 201)

   except Exception as e:
      print(str(e))
      response = 'Busy network. Try again later'
      return make_response(jsonify({'response':response}), 201)

# Response from dolt
@app.route('/user_query2', methods=['POST'])
def query_from_dolt():
   try:
      start_time = time.time()
      data = request.get_json()
      query = data['query']
      print(data)
      if 'user_id' in data:
         user_id = data['user_id']
      else:
         user_id = 1
      if 'assistant_id' in data:
         assistant_id = data['assistant_id']
      else :
         assistant_id = 1
      if user_id == '': # New user
         user_id = str(uuid.uuid4())
         user = User(user_id=user_id)
         db.session.add(user)
         db.session.commit()
      print(user_id)
      assistant = Assistant.query.filter_by(id = assistant_id).first()
      use_sql = assistant.use_sql
      use_pinecone = assistant.use_pinecone
      prompt = assistant.prompt

      chat_history = ChatHistory.query.filter_by(user_id=user_id).order_by(desc(ChatHistory.created_at)).limit(6).all()
      latest_records = [chat.json() for chat in chat_history]
      if use_sql == 1 and use_pinecone == 0:
         print('Only SQL>>>')
         response = query_with_dolt(query, prompt, assistant_id)
      if use_sql ==0 and use_pinecone == 1:
         print('Only Pinecone>>>')
         response = get_response(query=query, prompt=prompt, latest_records=latest_records, assistant_id=assistant_id)
      if use_sql ==0 and use_pinecone == 0:
         print('Only None>>>')
         response = simple_generate(query)
      if use_sql == 1 and use_pinecone == 1:
         response = query_with_both(query, prompt, assistant_id)
      closer_prompt = CloserPrompt.query.order_by(func.random()).first()
         
      pre_prompts= preprompt_generate(query)
      pre_prompts = pre_prompts.replace('1. ', '').replace('2. ', '').replace('3. ', '').replace('. ', '.').replace('"','')
      pre_prompts = pre_prompts.split('\n')
      
      new_chat = ChatHistory(user_id=user_id, user_query=query, response=response)
      db.session.add(new_chat)
      db.session.commit()
      end_time = time.time()
      print(f"The query took {end_time-start_time} seconds")
      print(new_chat.user_id)
      return make_response(jsonify({'response':response, 'closer':closer_prompt.prompt, 'pre_prompts':pre_prompts, 'chat_id':new_chat.user_id}), 201)
      
   except TypeError as e:
      print(str(e))
      response = 'Bad structure of database!'
      return make_response(jsonify({'response':response}), 201)
   except ValueError as e:
      print(str(e))
      response = 'Invalid value'
      return make_response(jsonify({'response':response}), 201)
   except Exception as e:
      print(str(e))
      response = 'Token limit'
      return make_response(jsonify({'response':response}), 201)


# Delete message 
@app.route('/del_message', methods = ['POST'])
def del_message():
   try:
      data = request.get_json()
      chat_id = data['chat_id']
      chat_history = ChatHistory.query.filter_by(id=chat_id).first()
      db.session.delete(chat_history)
      db.session.commit()
      return make_response(jsonify({'chat_id':chat_id}), 201)
   except:
      return make_response(jsonify({'result':'Failed!'}), 201)

# Get chat history
@app.route('/get_chat_history', methods =['POST'])
def get_chats():
   try:
      data = request.get_json()
      print(data)
      chat_id = data['user_id']
      if 'hsitory_id' in data:
         history_id = data['history_id']
         print('From shared history...')
         pre_chats = ChatHistory.query.filter_by(chat_id=chat_id).all()
         db.session.delete(pre_chats)
         db.session.commit()
         shared_chats = InheritChat.query.filter_by(history_id=history_id).all()
         for chat in shared_chats:
            new_chat = ChatHistory(chat_id=chat_id, user_query=chat.user_query, response=chat.response)
            db.session.add(new_chat)
            db.session.commit()
      chats = ChatHistory.query.filter_by(chat_id=chat_id).all()
      print('No shared')
      if chats:
         return make_response(jsonify([chat.json() for chat in chats]), 201)
      return make_response(jsonify({'result':'Not found!'}))
   except Exception as e:

      print(str(e))
      return make_response(jsonify({'result':'Server Error!'}), 201)

# Get and Add push prompt
@app.route('/push_prompt', methods = ['POST', 'GET'])
def push_prompt():
   if request.method == 'GET':
      try:
         assistant_id = request.args.get('assistant_id')
         with app.app_context():
            push_prompts = PushPrompt.query.filter_by(assistant_id=assistant_id).all()
         return make_response(jsonify([push_prompt.json() for push_prompt in push_prompts]), 200)
      except Exception as e:
         print(str(e))
         return make_response(jsonify({'prompts':'Error'}), 500)
   if request.method == 'POST':
      try:
         with app.app_context():
            data = request.get_json()
            prompt = data['prompt']
            assistant_id = data['assistant_id']
            push_prompt = PushPrompt(prompt=prompt, assistant_id= assistant_id)
            db.session.add(push_prompt)
            db.session.commit()
            # push_prompt = PushPrompt.query.filter_by(prompt=prompt).first()
            return make_response(jsonify(push_prompt.json()), 201)
      except Exception as e:
         print(str(e))
         return make_response(jsonify({'result':'Failed'}), 500)

# Get and add pre-prompt 
@app.route('/pre_prompt', methods = ['POST', 'GET'])
def pre_prompt():
   if request.method == 'GET':
      assistant_id = request.args.get('assistant_id')
      with app.app_context():
         pre_prompts = PrePrompt.query.filter_by(assistant_id=assistant_id).all()
         return make_response(jsonify([pre_prompt.json() for pre_prompt in pre_prompts]))
   
   if request.method == 'POST':
      try:
         with app.app_context():
            data = request.get_json()
            prompt = data['prompt']
            title = data['title']
            assistant_id = data['assistant_id']
            pre_prompt = PrePrompt(assistant_id=assistant_id, title=title ,prompt=prompt)
            db.session.add(pre_prompt)
            db.session.commit()
            return make_response(jsonify(pre_prompt.json()), 201)
      except Exception as e:
         print(str(e))
         return make_response(jsonify({'result':'Failed'}), 500) 

# Get and add closer prompt
@app.route('/closer_prompt', methods = ['POST', 'GET'])
def closer_prompt():

   if request.method == 'GET':
      assistant_id = request.args.get('assistant_id')

      with app.app_context():

         closer_prompts = CloserPrompt.query.filter_by(assistant_id=assistant_id).all()
         return make_response(jsonify([closer_prompt.json() for closer_prompt in closer_prompts]))
   
   if request.method == 'POST':
      try:
         with app.app_context():
            data = request.get_json()
            prompt = data['prompt']
            assistant_id = data['assistant_id']
            closer_prompt = CloserPrompt(assistant_id=assistant_id, prompt=prompt)
            db.session.add(closer_prompt)
            db.session.commit()
            # closer_prompt = CloserPrompt.query.filter_by(prompt=prompt).first()
            return make_response(jsonify(closer_prompt.json()), 201)
      except Exception as e:
         print(str(e))
         return make_response(jsonify({'result':'Failed'}), 500)
      
#  Delete push prompt
@app.route('/del_push_prompt', methods=['POST'])
def delete_push_prompt():
   try:
      with app.app_context():
         data = request.get_json()
         id = data['id']
         push_prompt = PushPrompt.query.filter_by(id=id).first()
         if push_prompt:
            db.session.delete(push_prompt)
            db.session.commit()
            return make_response(jsonify({'id':id}), 200)
      return make_response(jsonify({'message':'Not found!'}), 404)
   except Exception as e:
      print(str(e))
      return make_response(jsonify({'message':'Error deleting'}), 500)

#  Delete pre prompt
@app.route('/del_pre_prompt', methods=['POST'])
def delete_pre_prompt():
   try:
      with app.app_context():
         data = request.get_json()
         id = data['id']
         pre_prompt = PrePrompt.query.filter_by(id=id).first()
         if pre_prompt:
            db.session.delete(pre_prompt)
            db.session.commit()
            return make_response(jsonify({'id':id}), 200)
      return make_response(jsonify({'message':'Not found!'}), 404)
   except Exception as e:
      print(str(e))
      return make_response(jsonify({'message':'Error deleting'}), 500)
   
# Delete closer prompt
@app.route('/del_closer_prompt', methods=['POST'])
def delete_closer_prompt():
   try:
      with app.app_context():
         data = request.get_json()
         id = data['id']
         closer_prompt = CloserPrompt.query.filter_by(id=id).first()
         if closer_prompt:
            db.session.delete(closer_prompt)
            db.session.commit()
            return make_response(jsonify({'id':id}), 200)
      return make_response(jsonify({'message':'Not found!'}), 404)
   except Exception as e:
      print(str(e))
      return make_response(jsonify({'message':'Error deleting'}), 500)

# Update pre-prompt
@app.route('/update_pre_prompt', methods=['POST'])
def update_pre_prompt():
   try:
      with app.app_context():
         data = request.get_json()
         id = data['id']
         prompt = data['prompt']
         title = data['title']
         pre_prompt = PrePrompt.query.filter_by(id=id).first()
         if pre_prompt:
            pre_prompt.title = title
            pre_prompt.prompt = prompt
            db.session.commit()
            return make_response(jsonify(pre_prompt.json()), 200)
         return make_response(jsonify({'message':'Not found!'}), 404)
   except Exception as e:
      print(str(e))
      return make_response(jsonify({'message':'Already exits!'}), 500)

# Update push-prompt
@app.route('/update_push_prompt', methods=['POST'])
def update_push_prompt():
   try:
      with app.app_context():
         data = request.get_json()
         id = data['id']
         prompt = data['prompt']
         push_prompt = PushPrompt.query.filter_by(id=id).first()
         if push_prompt:
            push_prompt.prompt = prompt
            db.session.commit()
            return make_response(jsonify(push_prompt.json()), 200)
         return make_response(jsonify({'message':'Not found!'}), 404)
   except Exception as e:
      print(str(e))
      return make_response(jsonify({'message':'Already exits!'}), 500)

# Update pre-prompt
@app.route('/update_closer_prompt', methods=['POST'])
def update_closer_prompt():
   try:
      with app.app_context():
         data = request.get_json()
         id = data['id']
         prompt = data['prompt']
         closer_prompt = CloserPrompt.query.filter_by(id=id).first()
         if closer_prompt:
            closer_prompt.prompt = prompt
            db.session.commit()
            return make_response(jsonify(closer_prompt.json()), 200)
         return make_response(jsonify({'message':'Not found!'}), 404)
   except Exception as e:
      print(str(e))
      return make_response(jsonify({'message':'Already exits!'}), 500)

#  Add a new knowledge to a certain assistant
@app.route('/add_knowledge', methods=['POST'])
def add_knowledge():
   if 'assistant_id' in request.form:
      assistant_id = request.form['assistant_id']
      
      file = request.files.get('file')
      if file:
         try:
            print('Get files...')
            if file.filename=='':
               print('No selected file...')
            extension = file.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(file.filename)
            save_path = app.config['UPLOAD_FOLDER']+ filename
            file.save(save_path)
            new_knowledge = KnowledgeBase(assistant_id=assistant_id, name=filename, type_of_knowledge=extension)
            db.session.add(new_knowledge)
            db.session.commit()
            print('Succesfully saved a file')
            # Save to pinecone
            assistant = Assistant.query.filter_by(id=assistant_id).first()
            pinecone_api_key = assistant.pinecone_api_key
            pinecone_environment = assistant.pinecone_environment
            pinecone_index_name = assistant.pinecone_index_name

            generate_kb_from_file(assistant_id, new_knowledge.id, save_path, pinecone_api_key, pinecone_environment, pinecone_index_name)
            
            return make_response(jsonify(new_knowledge.json()), 201)
         except Exception as e:
            print(str(e))
            return make_response(jsonify({'result':'Failed!'}), 500)
      if 'knowledge_name' in request.form :
         knowledge_name = request.form['knowledge_name']
         if knowledge_name:
            with app.app_context():
               try:
                  new_knowledge = KnowledgeBase(assistant_id=assistant_id, name=knowledge_name, type_of_knowledge='URL')
                  db.session.add(new_knowledge)
                  db.session.commit()
                  res = generate_kb_from_url(assistant_id=assistant_id, knowledge_id=new_knowledge.id, url=knowledge_name)
                  if res is False:
                     return make_response(jsonify({'result':'Invalid URL'}), 200)
                  print('Successfully saved a URL')
                  return make_response(jsonify(new_knowledge.json()), 200)
               except Exception as e:
                  print(str(e))
                  return make_response(jsonify({'result':'Failed!'}), 201)
   return make_response(jsonify({'result':'Invalid data format'}), 500)

# Get knowledge bases for a specific assistant_id
@app.route('/get_knowledge', methods = ['POST'])
def get_knowledge():
   data = request.get_json()
   assistant_id = data['assistant_id']
   print(data)
   with app.app_context():
      try:
         knowledge_bases = KnowledgeBase.query.filter_by(assistant_id=assistant_id).all()
         if knowledge_bases:
            print(knowledge_bases[0].json())
            return make_response(jsonify([knowledge_base.json() for knowledge_base in knowledge_bases]), 200)
         return make_response(jsonify({'result':'Not found'}), 200)
      except Exception as e:
         print(str(e))
         return make_response(jsonify({'result':'Failed!'}), 500)

# Delete knowledge base for a specific knowledge_id
@app.route('/del_knowledge', methods=['POST'])
def delete_knowledge():
   try:
      with app.app_context():
         data = request.get_json()
         id = data['id']
         assistant_id = data['assistant_id']
         knowledge_base = KnowledgeBase.query.filter_by(id=id).first()
         if knowledge_base:
            db.session.delete(knowledge_base)
            db.session.commit()
            # Delete knowledge in pinecone
            del_knowledge_by_knowledge_id(id, assistant_id)
            return make_response(jsonify({'id':id}), 200)
         return make_response(jsonify({'message':'Not found!'}), 404)
   except Exception as e:
      print(str(e))
      return make_response(jsonify({'message':'Error deleting'}), 500)

# Add a new assistant
@app.route('/add_assistant', methods=['POST'])
def add_assistant():
   data = request.get_json()
   assistant_name = data['assistant_name']
   prompt = data['prompt']
   use_sql = data['use_sql']
   use_pinecone = data['use_pinecone']
   use_serp = data['use_serp']
   if use_sql:
      sql_host = data['sql_host']
      sql_username = data['sql_username']
      sql_password = data['sql_password']
      sql_db_name = data['sql_db_name']
      sql_port = data['sql_port']
   else:
      sql_host = ''
      sql_username = ''
      sql_password = ''
      sql_db_name = ''
      sql_port = ''
   if use_pinecone:
      pinecone_api_key = data['pinecone_api_key']
      pinecone_environment = data['pinecone_environment']
      pinecone_index_name = data['pinecone_index_name']
   else:
      pinecone_api_key = ''
      pinecone_environment = ''
      pinecone_index_name = ''

   with app.app_context():
      try:
         new_assistant = Assistant(name=assistant_name, prompt=prompt, use_sql=use_sql,use_pinecone=use_pinecone,use_serp=use_serp, sql_host=sql_host, sql_username=sql_username, sql_password=sql_password, sql_port=sql_port, sql_db_name=sql_db_name, pinecone_api_key=pinecone_api_key, pinecone_environment=pinecone_environment, pinecone_index_name=pinecone_index_name)
         db.session.add(new_assistant)
         db.session.commit()
         print('Successfully saved assistant')
         return make_response(jsonify(new_assistant.json()),201)
      except Exception as e:
         print(str(e))
         return make_response(jsonify({'result':'Error saving'}))
      
# Get assistants
@app.route('/get_assistant', methods=['GET'])
def get_assistant():
   with app.app_context():
      try:
         assistants = Assistant.query.all()
         return make_response(jsonify([assistant.json() for assistant in assistants]))
      except Exception as e:
         print(str(e))
         return make_response(jsonify({'result':'Database Error'}))

# Delete an assistant
@app.route('/del_assistant', methods=['POST'])
def del_assistant():
   data = request.get_json()
   id = data['id']
   with app.app_context():
      try:
         assistant = Assistant.query.filter_by(id=id).first()
         if assistant:
            db.session.delete(assistant)
            db.session.commit()
         del_knowledgebase_by_assistant_id(id)
         return make_response(jsonify({'id':id}))
      except:
         return make_response(jsonify({'result':'Failed!'}))

# Update the name of assistant
@app.route('/update_assistant', methods=['POST'])
def update_assistant():
   try:
      data = request.get_json()
      id = data['id'] 
      prompt = data['prompt']
      assistant_name = data['assistant_name']
      use_sql = data['use_sql']
      use_serp = data['use_serp']
      use_pinecone = data['use_pinecone']
      if use_sql:
         sql_host = data['sql_host']
         sql_username = data['sql_username']
         sql_password = data['sql_password']
         sql_db_name = data['sql_db_name']
         sql_port = data['sql_port']
      else:
         sql_host = ''
         sql_username = ''
         sql_password = ''
         sql_db_name = ''
         sql_port = ''
      if use_pinecone:
         pinecone_api_key = data['pinecone_api_key']
         pinecone_environment = data['pinecone_environment']
         pinecone_index_name = data['pinecone_index_name']
      else:
         pinecone_api_key = ''
         pinecone_environment = ''
         pinecone_index_name = ''
      assistant = Assistant.query.filter_by(id=id).first()
      if assistant:
         assistant.name = assistant_name
         assistant.prompt = prompt
         assistant.use_sql = use_sql
         assistant.use_pinecone = use_pinecone
         assistant.use_serp = use_serp
         assistant.sql_host = sql_host
         assistant.sql_username = sql_username
         assistant.sql_password = sql_password
         assistant.sql_db_name = sql_db_name
         assistant.sql_port = sql_port
         assistant.pinecone_api_key = pinecone_api_key
         assistant.pinecone_environment = pinecone_environment
         assistant.pinecone_index_name = pinecone_index_name

         db.session.commit()
         return make_response(jsonify(assistant.json()), 201)
      return make_response(jsonify({'result':'Not found'}), 201)
   except Exception as e:
      print(str(e))
      return make_response(jsonify({'result':'Failed'}), 500)

# Get the first 3 random pre-prompts
@app.route('/get_initial_prompts', methods=['GET'])
def get_initial_prompts():
   assistant_id = request.args.get('assistant_id')
   row_count = PrePrompt.query.count()
   if row_count > 2:
      preprompts = PrePrompt.query.filter_by(assistant_id=assistant_id).order_by(func.random()).limit(3)
      print(preprompts)
      return make_response(jsonify([preprompt.json() for preprompt in preprompts]), 200)
   if row_count > 0:
      preprompts = PrePrompt.query.all()
      return make_response(jsonify([preprompt.json() for preprompt in preprompts]))

   return make_response(jsonify({'result':'None'}))

# Share the link[]
@app.route('/share_chat', methods = ['POST'])
def share_chat():
   try:
      data = request.get_json()
      user_id = data['user_id']

      user = User.query.filter_by(id=user_id).first()
      if user.shared == 0:
         user.shared = 1
         history_id = str(uuid.uuid4())
         user.history_id = history_id
         with app.app_context():
            chats = ChatHistory.query.filter_by(user_id=user_id).all()
            for chat in chats:
               new_history = InheritChat(history_id=history_id, user_query=chat.user_query, response=chat.response)
               db.session.add(new_history)
               db.session.commit()
         return make_response(jsonify({'history_id':history_id}), 201)
      history_id = user.history_id
      return make_response(jsonify({'history_id':history_id}), 201)

   except Exception as e:
      print(str(e))
      return make_response(jsonify({'result':'Failed!'}), 500)
   
# Test SQL connection
@app.route('/test_sql_connection', methods =['POST'])
def test_sql_connection():
   try:
      data = request.get_json()
      host = data['host']
      username = data['username']
      password = data['password']
      db_name = data['db_name']
      port = data['port']
      db = sql_connect(host=host, username=username, port=port, password=password, db_name=db_name)
      
      if db:
         db.close()
         return make_response(jsonify({'result':True}), 200)
      else:
         return make_response(jsonify({'result':True}), 200)
      
   except Exception as e:
      print(str(e))
      return make_response(jsonify({'result':'Busy server. Try again later!'}), 500)

# Test Pinecone connections
@app.route('/test_pinecone_connection', methods = ['POST'])
def test_pinecone_connection():
   try:
      data = request.get_json()
      api_key = data['api_key']
      environment = data['environment']
      index_name = data['index_name']
      res = pinecone_connect(api_key=api_key, environment=environment, index_name=index_name)
      print(res.describe_index_stats())
      if res:
         return make_response(jsonify({'result':True}), 200)
   except Exception as e:
      print(str(e))
      return make_response(jsonify({'result':False}), 200)


if __name__ == '__main__':
   app.run(debug=True)
   
   