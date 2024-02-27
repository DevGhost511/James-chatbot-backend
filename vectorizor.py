
import openai
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
import time
from uuid import uuid4
import pymysql
# from langchain.vectorstores import Pinecone
from langchain.utilities import SQLDatabase, GoogleSerperAPIWrapper
from langchain.prompts.chat import ChatPromptTemplate
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.agents.agent_types import AgentType
from langchain_experimental.sql import SQLDatabaseChain
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chains.question_answering import load_qa_chain
import mysql.connector
from langchain.agents import create_sql_agent, initialize_agent, Tool
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain_openai import OpenAI
from langchain.schema import SystemMessage, HumanMessage
from langchain_core.runnables import RunnablePassthrough
from sqlalchemy import create_engine
from urllib.parse import quote

from models import KnowledgeBase
from sqlalchemy.engine.url import URL
# from langchain.sql_database import SQLDatabase
from models import Assistant, KnowledgeBase
# from langchain import LargeLanguageModel
import os
import base64
import requests
from dotenv import load_dotenv
from chunker import getPineconeFromIndex, saveToPinecone
load_dotenv()

# Set up OpenAI and Pinecone API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("INDEX_NAME")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
PINECONE_INDEX_DIMENSION = os.getenv("PINECONE_INDEX_DIMENSION")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
DOLT_HOST = os.getenv("DOLT_HOST")
DOLT_PORT = os.getenv("DOLT_PORT")
DOLT_USERNAME = os.getenv("DOLT_USERNAME")
DOLT_PASSWORD = os.getenv("DOLT_PASSWORD")
DOLT_DATABASE = os.getenv("DOLT_DATABASE")

# db = mysql.connector.connect(
#     host = DOLT_HOST,
#     user = DOLT_USERNAME,
#     password = DOLT_PASSWORD,
#     database = DOLT_DATABASE
# )

print(SERPER_API_KEY)
openai.api_key = OPENAI_API_KEY

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Messaging image
def image_qeury(query, image_path):
    base64_image = encode_image(image_path)
    # print("Base64 code >>>>", base64_image)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    payload = {
        "model":"gpt-4-vision-preview",
        "messages":[
            {
                "role":"user",
                "content":[
                    {    
                        "type":"text",
                        "text":query
                    },
                    {
                        "type":"image_url",
                        "image_url": {
                            "url":f"data:image/jpeg;base64, {base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 4096
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    print(response.json())
    return response.json()

# Connect to SQL
def sql_connect(host, port, username, password, db_name):
    try:
        db = mysql.connector.connect(
            host = host,
            port = port,
            user = username,
            password = password,
            database = db_name
        )
        return db
    except:
        return None

# Connect to Pinecone
def pinecone_connect(api_key, environment, index_name):
    try:
        pinecone = Pinecone(api_key=api_key)
        if index_name not in pinecone.list_indexes().names():
            return {"success": False, "message": "There is no such an index"}
               
        
        index = pinecone.Index(index_name)
        print("Index is ----->", index)
        return {"success": True, "message": "Index created successfully.", "index": index}
    except Exception as e:
        error_message = str(e)
        print(error_message)
        return {"success": False, "message": f"Error: {error_message}"}

# The response will be a string that is a question
def query_refiner(conversation, query):
    response = openai.Completion.create(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Who won the world series in 2020?"}
        ]
    )
    return response.choices[0].message.content

def preprompt_generate(query, assistant_id):
    limit = ''
    if assistant_id == 5:
        limit = ' Each query must be less than 20 characters'
    prompt = f'Q: Give me 3 different related queries with {query}.{limit} A:'
    response = openai.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": "You are a helpful related topic generator. Only provide 3 topics at once."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content


def simple_generate(query):
    response = openai.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": query}
        ]
    )
    return response.choices[0].message.content

# Generate the answer 
def generate_answer(query, assistant_id, template, latest_records):
    prompt = PromptTemplate(
        input_variables=["chat_history", "human_input", "context"],
        template=template
    )
    assistant = Assistant.query.filter_by(id=assistant_id).first()
    api_key = assistant.pinecone_api_key
    environment = assistant.pinecone_environment
    index_name = assistant.pinecone_index_name
    memory = ConversationBufferMemory(memory_key="chat_history", input_key="human_input")
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

    docsearch = getPineconeFromIndex(index_name)

    docs = docsearch.similarity_search(query, k=8, filter={'assistant': (assistant_id)})
    # print(docs)
    chat_openai = OpenAI(temperature = 0.7, model = "gpt-4-turbo-preview", openai_api_key = OPENAI_API_KEY)

    chain = load_qa_chain(chat_openai, chain_type="stuff", prompt=prompt, memory=memory)
    if len(latest_records) == 0:
        print("No history>..")
    for index, record in enumerate(latest_records):
        # print(record['user_query'])
        chain.memory.save_context({'human_input':record['user_query']}, {'output':record['response']})
    
    
    output = chain ({'input_documents':docs, 'human_input': query}, return_only_outputs=False)   
    chain.memory.clear()

    return output['output_text']

# Generating Text Embeddings with OpenAI's API
def generate_text_embeddings(text_chunks):
    embeddings = []
    for chunk in text_chunks:
        response = openai.embeddings.create(input=chunk, model="text-embedding-ada-002")
        embeddings.append(response['data'][0]['embedding'])
    return embeddings

# Initialize Pinecone index
def init_pinecone(index_name, dimension):
    pinecone = Pinecone(api_key=PINECONE_API_KEY)
    if index_name not in pinecone.list_indexes().names():
        pinecone.create_index(
            name=index_name, 
            dimension=dimension, 
            spec=ServerlessSpec(
                cloud="aws",
                region="us-west-2"
            )
        )
    return pinecone.Index(index_name)

# Storing and Retrieving Embeddings with Pinecone credentials
def store_embeddings_in_pinecone(chunks, metalist, pinecone_api_key, ids, pinecone_index_name):
    try:
        if pinecone_api_key is not None:
            PINECONE_API_KEY = pinecone_api_key
        
        if pinecone_index_name is not None:
            PINECONE_INDEX_NAME = pinecone_index_name 
        # pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        saveToPinecone(chunks, embeddings, PINECONE_INDEX_NAME, metalist, ids)
        
        print("Success embedding...")
        return True
    except Exception as e:
        print("Error embedding...", str(e))
        return False

def retrieve_embeddings_from_pinecone(index_name, query_embedding):
    pinecone = Pinecone(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
    vector_store = pinecone.Index(index_name)
    results = vector_store.query(queries=query_embedding)
    return results

# Delete all records of the index
def del_all_records(assistant_id):
    try:
        assistant = Assistant.query.filter_by(id=assistant_id).first()
        pinecone_api_key = assistant.pinecone_api_key
        pinecone_environment = assistant.pinecone_environment
        pinecone_index_name = assistant.pinecone_index_name
        index = pinecone_connect(pinecone_api_key, pinecone_environment, pinecone_index_name)
        index.delete(delete_all=True)
        return True
    except Exception as e:
        print(str(e))
        return False

def del_knowledgebase_by_assistant_id(assistant_id):
    try :
        assistant = Assistant.query.filter_by(assistant_id=assistant_id).first()
        api_key = assistant.pinecone_api_key
        environment = assistant.pinecone_environment
        index_name = assistant.pinecone_index_name
        pinecone=Pinecone(api_key=api_key)
        index = pinecone.Index(index_name)      
        index.delete(
            filter={
                'assistant':assistant_id
            }
        )
        print('Deleted assistant ', assistant_id)
        return True
    except Exception as e:
        print(str(e))
        return False

def del_knowledge_by_knowledge_id(knowledge_id, assistant_id):
    try:
        # print("knowledge_id >>", assistant_id)
        assistant = Assistant.query.filter_by(id=assistant_id).first()
        api_key = assistant.pinecone_api_key
        environment = assistant.pinecone_environment
        index_name = assistant.pinecone_index_name
        pinecone=Pinecone(api_key=api_key)
        index = pinecone.Index(index_name)
        knowledge_base = KnowledgeBase.query.filter_by(id=knowledge_id).first()
        
        count = knowledge_base.count
        ids = [f"{knowledge_id}_{i}" for i in range(count)]
        print(knowledge_id, count)

        print(ids)
        index.delete(ids=ids)
        print("Deletion success!")
        return True
    except Exception as e:
        print(str(e))
        return False

# Create embeddings and populate the index with the train data
def create_and_index_embeddings(text_chunks, metalist):
    
    # Initialize Pinecone index
    try:
        chatgpt_index = init_pinecone(INDEX_NAME)
        embeddings = generate_text_embeddings(text_chunks)
        for embedding in embeddings:
            chatgpt_index.upsert(items=[embedding], metadata = [metalist])
    except Exception as e:
        print(e)
    return chatgpt_index

# Query with database
def query_with_dolt(query, prompt, assistant_id):
    # sql_db = SQLDatabase.from_dbapi(db)
    assistant = Assistant.query.filter_by(id=assistant_id).first()
    sql_host = assistant.sql_host
    sql_username = assistant.sql_username
    sql_password = assistant.sql_password
    sql_db_name = assistant.sql_db_name
    final_prompt = ChatPromptTemplate.from_messages(
        [
            ("system",
             prompt
            ),
            ("user", "{question}\n ai: "),
        ]
    )
    db = SQLDatabase.from_uri(f"mysql+mysqldb://{sql_username}:{sql_password}@{sql_host}/{sql_db_name}?ssl=1")
    llm = ChatOpenAI (temperature=0, model='gpt-4-turbo-preview')
    tookkit = SQLDatabaseToolkit(db=db, llm=llm)
    agent_executor = create_sql_agent(
        llm=llm,
        toolkit=tookkit,
        verbose=True,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    )
    
    res = agent_executor.run(final_prompt.format(question=query))
    # print(res)
    return res

def query_with_both(query, prompt, assistant_id):
    assistant = Assistant.query.filter_by(id=assistant_id).first()
    sql_host = assistant.sql_host
    sql_username = assistant.sql_username
    sql_password = assistant.sql_password
    sql_port = assistant.sql_port
    sql_db_name = assistant.sql_db_name
    pinecone_index_name = assistant.pinecone_index_name
    pinecone_environment = assistant.pinecone_environment
    pinecone_api_key = assistant.pinecone_api_key


    
    memory = ConversationBufferMemory(memory_key="chat_history", input_key="human_input")
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

    docsearch =  getPineconeFromIndex(pinecone_index_name)

    docs = docsearch.similarity_search(query, k=8, filter={'assistant': (assistant_id)})
    starter = f"Use this one of knowledge base: {docs}"
    # sql_db = SQLDatabase.from_dbapi(db)
    final_prompt = ChatPromptTemplate.from_messages(
        [
            ("system",
             starter+prompt
            ),
            ("user", "{question}\n ai: "),
        ]
    )
    db = SQLDatabase.from_uri(f"mysql+mysqldb://{sql_username}:{sql_password}@{sql_host}/{sql_db_name}?ssl=1")
    llm = ChatOpenAI (temperature=0, model='gpt-4-turbo-preview')

    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    agent_executor = create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        verbose=True,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    )
    
    res = agent_executor.run(final_prompt.format(question=query))
    # print(res)
    return res

# Get result from pinecone
def pinecone_result(assistant_id, query):
    try:
        start_time = time.time()
        assistant = Assistant.query.filter_by(id=assistant_id).first()
        pinecone_api_key = assistant.pinecone_api_key
        pinecone_environment = assistant.pinecone_environment
        pinecone_index_name = assistant.pinecone_index_name

        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

        docsearch = getPineconeFromIndex(pinecone_index_name)
        print("Assistant id >>>", assistant_id)
        docs = docsearch.similarity_search(query, k=8, filter={'assistant': str(assistant_id)})
        print("Pinecone Result >>>", docs)
        end_time = time.time()
        print(f'>>> Pinecone search takes {end_time-start_time} seconds')

        return docs[0].page_content
    except Exception as e:
        print(str(e))
        return 'There is no relevant information.'

# Get result from SERP
def serp_result(query):
    try:
        start_time = time.time()
        llm = OpenAI(temperature=0, model="gpt-4-turbo-preview")
        search = GoogleSerperAPIWrapper()

        tools = [
            Tool(
                name="Intermediate Answer",
                func=search.run,
                description="userful for when you need to ask with google search"
            )
        ]
        result = search.results(query)
        end_time = time.time()
        print('SERP Result >>>', result)
        print(f'>>> Google search takes {end_time-start_time} seconds')
        return result
       
    except Exception as e:
        print(str(e))
        return 'There is no relevant information.'

# Generate an image for surf bot  
def generate_surfing_image(surf_instructions, beach):
    try:
        image_prompt = f"Real Photo of someone surfing the best wave at {beach}. Put someone at this location, on a wave, and on this board doing this surf style. make sure the physics of the surfer angle based on the wave is correct positioning, human photo realistic. No words or text"
        print("Generating surfing image with prompt:", image_prompt)
        headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }
        payload = {
            "model": "dall-e-3",
            "prompt": image_prompt,
            "n": 1,
            "size": "1024x1024",
            "response_format":"url"
        }
        response = requests.post("https://api.openai.com/v1/images/generations", headers=headers, json=payload)
        # print(response.json())
        json_res = response.json()
        print("Json data of image url >>>>>", json_res)
        image_url = json_res["data"][0]["url"]
        print("Generated Surfing Image URL: %s", image_url)
        return image_url
    except Exception as e:
        print("Failed to generate surfing image: %s", e)
        return None

# Generate an image using dall-e-3 model
def generate_image(query):
    try:
        descriptive_prompt = "Imagine you are making an image of this finished cooked meal. Include descriptive terms related to the dish itself, such as its appearance, colors, textures, arrangement, and any unique presentation details. Also, consider aspects like lighting, angles, and settings to enhance the visual appeal of the dish."
    
        print("Generating images...")
        headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }

        prompt = "Content: " +descriptive_prompt+" + Recipe: "+ query + "including camera and lighting and quality angles of variations and unique image locations. be descriptive like a photographer describing, no rustic"
        print("Prompt >>>", prompt)
        payload = {
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "response_format":"url"
        }
        response = requests.post("https://api.openai.com/v1/images/generations", headers=headers, json=payload)
        # print(response.json())
        json_res = response.json()
        print("Json data of image url >>>>>", json_res)
        image_url = json_res["data"][0]["url"]
        return image_url
    except Exception as e:
        print(str(e))
        return str(e)

# Get result from sql
def sql_result(assistant_id, query):
    try:
        start_time = time.time()
        assistant = Assistant.query.filter_by(id=assistant_id).first()
        sql_host = assistant.sql_host
        sql_username = assistant.sql_username
        sql_password = quote(assistant_sql_password, safe='')
        sql_port = assistant.sql_port
        sql_db_name = assistant.sql_db_name
         
        connection_string = f'mysql+mysqldb://{sql_username}:{sql_password}@{sql_host}:{sql_port}/{sql_db_name}?ssl=1'
 
        db = SQLDatabase.from_uri(connection_string)
        print("DB connected to>>>", db)
        llm = ChatOpenAI (temperature=0, model='gpt-4-turbo-preview')
        toolkit = SQLDatabaseToolkit(db=db, llm=llm)
        agent_executor = create_sql_agent(
            llm=llm,
            toolkit=toolkit,
            verbose=True,
            agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        )
        prompt = assistant.prompt
        template = prompt + query
        # question = template.format(question=query)

        result = agent_executor.run(template)
        end_time = time.time()
        
        print("SQL Result >>>", result)
        print(f'>>> SQL query takes {end_time-start_time} seconds')

        return result
    except Exception as e:
        print(str(e))
        return 'There is no relevant information.'

# Generate answers with all results
def generate_final_answer(assistant_id, query):
    try:
        start_time = time.time()
        assistant = Assistant.query.filter_by(id=assistant_id).first()
        if assistant.use_pinecone:
            pinecone_res = pinecone_result(assistant_id, query)
        else:
            pinecone_res = 'There is no relevant information'
        if assistant.use_serp:
            serp_res = serp_result(query)
        else:
            serp_res = 'There is no relevant information'
        if assistant.use_sql:
            sql_res = sql_result(assistant_id, query)
        else:
            sql_res = 'There is no relevant information'
        preprompt = assistant.prompt
        template = """{preprompt}\nThere are 3 kind of knowledge base for given information: SQL Results, Pinecone Restuls and SERp Results. Summarize the information to give a helpful assistant to users. If there is no relevant information, Give me general ideal to user. Don't indicate that where the info is from.
            SQL Results:{sql_result}
            Pinecone Results:{pinecone_result}
            SERP Results:{serp_result}
            Human: {human_input}
            Assistant:"""
        prompt = PromptTemplate.from_template(template)
        # print(template)
        question = prompt.format(
            preprompt = preprompt,
            sql_result= sql_res,
            pinecone_result = pinecone_res,
            serp_result = serp_res,
            human_input = query
        )

        print("Template >>>", question)


        llm = ChatOpenAI (temperature=0, model='gpt-4-turbo-preview')
        messages = [
            SystemMessage(
                content= "You are a helpful assistant that privdes relevant answers"
            ),
            HumanMessage(
                content=question
            )
        ]
        result = llm(messages)

        end_time = time.time()
        print(f'Final query takes {end_time-start_time} seconds')

        return result.content
    except Exception as e:
        print(str(e))
        return "Error"
    

