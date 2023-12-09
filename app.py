import os
import urllib.parse as up
from dotenv import load_dotenv
from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy

# from utils import generate_kb, generate_kb_from_txt
from flask_cors import CORS
import psycopg2
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from utils import get_response
from utils import generate_kb_from_file
from models import db, PushPrompt, PrePrompt, CloserPrompt, KnowledgeBase, Assistant

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
   return "This is an api for CustomGPT!"

# Response to the query
@app.route('/user_query', methods=['POST'])
def query():
   data = request.get_json()
   print(data)
   query = data['query']
   response = get_response(query)
   print(response)
   return jsonify({'response':response})

# Get and Add push prompt
@app.route('/push_prompt', methods = ['POST', 'GET'])
def push_prompt():
   if request.method == 'GET':
      try:
         with app.app_context():
            push_prompts = PushPrompt.query.all()
         return make_response(jsonify([push_prompt.json() for push_prompt in push_prompts]), 200)
      except Exception as e:
         print(str(e))
         return make_response(jsonify({'prompts':'Error'}), 500)
   if request.method == 'POST':
      try:
         with app.app_context():
            data = request.get_json()
            prompt = data['prompt']
            push_prompt = PushPrompt(prompt=prompt)
            db.session.add(push_prompt)
            db.session.commit()
            push_prompt = PushPrompt.query.filter_by(prompt=prompt).first()
         return make_response(jsonify(push_prompt.json()), 201)
      except Exception as e:
         print(str(e))
         return make_response(jsonify({'result':'Failed'}), 500)

# Get and add pre-prompt 
@app.route('/pre_prompt', methods = ['POST', 'GET'])
def pre_prompt():
   if request.method == 'GET':
      with app.app_context():
         pre_prompts = PrePrompt.query.all()
         return make_response(jsonify([pre_prompt.json() for pre_prompt in pre_prompts]))
   
   if request.method == 'POST':
      try:
         with app.app_context():
            data = request.get_json()
            prompt = data['prompt']
            title = data['title']
            pre_prompt = PrePrompt(title=title ,prompt=prompt)
            db.session.add(pre_prompt)
            db.session.commit()
            pre_prompt = PrePrompt.query.filter_by(title=title).first()
            return make_response(jsonify(pre_prompt.json()), 201)
      except Exception as e:
         print(str(e))
         return make_response(jsonify({'result':'Failed'}), 500) 

# Get and add closer prompt
@app.route('/closer_prompt', methods = ['POST', 'GET'])
def closer_prompt():
   if request.method == 'GET':
      with app.app_context():
         closer_prompts = CloserPrompt.query.all()
         return make_response(jsonify([closer_prompt.json() for closer_prompt in closer_prompts]))
   
   if request.method == 'POST':
      try:
         with app.app_context():
            data = request.get_json()
            prompt = data['prompt']
            closer_prompt = CloserPrompt(prompt=prompt)
            db.session.add(closer_prompt)
            db.session.commit()
            closer_prompt = CloserPrompt.query.filter_by(prompt=prompt).first()
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
            new_knowledge = KnowledgeBase.query.filter_by(name=filename).first()
            print('Succesfully saved a file')
            # Save to pinecone
            generate_kb_from_file(assistant_id, new_knowledge.id, save_path)
            
            return make_response(jsonify(new_knowledge.json()), 201)
         except Exception as e:
            print(str(e))
            return make_response(jsonify({'result':'Failed!'}), 500)
      knowledge_name = request.form['knowledge_name']
      if knowledge_name:
         with app.app_context():
            try:
               new_knowledge = KnowledgeBase(assistant_id=assistant_id, name=knowledge_name, type_of_knowledge='URL')
               db.session.add(new_knowledge)
               db.session.commit()
               new_knowledge = KnowledgeBase.query.filter_by(name=knowledge_name).first()

               print('Successfully saved a URL')
               return make_response(jsonify(new_knowledge.json()), 201)
            except Exception as e:
               print(str(e))
               return make_response(jsonify({'result':'Failed!'}))
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
         knowledge_base = KnowledgeBase.query.filter_by(id=id).first()
         if knowledge_base:
            db.session.delete(knowledge_base)
            db.session.commit()
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
   
   with app.app_context():
      try:
         new_assistant = Assistant(name=assistant_name)
         db.session.add(new_assistant)
         db.session.commit()
         new_assistant = Assistant.query.filter_by(name=assistant_name).first()
         print('Successfully saved assistant')
         return make_response(jsonify(new_assistant.json()))
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
   




if __name__ == '__main__':
   
   app.run(debug=True)
   
   