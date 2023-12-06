import os
import urllib.parse as up
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from utils import get_response
from utils import generate_kb
# from flask_cors import CORS

app = Flask(__name__)
# CORS(app)

load_dotenv()

up.uses_netloc.append("postgres")
url = up.urlparse(os.getenv("DATABASE_URL"))
# try :
#    conn = psycopg2.connect(database=url.path[1:],
#                            user = url.username,
#                            password= url.password,
#                            host=url.hostname,
#                            port=url.port)
#    print(f"Connected to database: {url.path[1:]}")
# except :
#    print(f"Error connecting to database: {os.getenv('DATABASE_URL')}")

@app.route("/")
def index():
   return "This is an api for CustomGPT!"

@app.route('/query', methods=['POST'])
def query():
   data = request.get_json()
   print(data)
   query = data['query']
   response = get_response(query)
   print(response)
   return jsonify({'response':response})


if __name__ == '__main__':
   #  generate_kb()
    
    app.run(debug=True, port='0.0.0.0')