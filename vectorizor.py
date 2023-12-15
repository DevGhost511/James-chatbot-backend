
import openai
import pinecone
from uuid import uuid4
import pymysql
from langchain.vectorstores import Pinecone
from langchain.utilities import SQLDatabase
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.llms import OpenAI
from langchain.agents.agent_types import AgentType
from langchain_experimental.sql import SQLDatabaseChain
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chains.question_answering import load_qa_chain
import mysql.connector
from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.llms.openai import OpenAI
# from langchain import LargeLanguageModel
import os
from dotenv import load_dotenv

load_dotenv()


# Set up OpenAI and Pinecone API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
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

db = mysql.connector.connect(
    host = DOLT_HOST,
    user = DOLT_USERNAME,
    password = DOLT_PASSWORD,
    database = DOLT_DATABASE
)

print(PINECONE_INDEX_NAME)
openai.api_key = OPENAI_API_KEY
# Prepare pinecone
pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
index = pinecone.Index('custom-gpt')

# The response will be a string that is a question
def query_refiner(conversation, query):
    response = openai.Completion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Who won the world series in 2020?"}
        ]
    )
    return response.choices[0].message.content

def simple_generate(query):
    prompt = f'Q: Give me 3 different related queries with {query}. A:'
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful related topic generator. Only provide 3 topics at once."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

# Generate the answer 
def generate_answer(query, template, user_id, knowledge_name, latest_records):
    prompt = PromptTemplate(
        input_variables=["chat_history", "human_input", "context"],
        template=template
    )

    pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
    memory = ConversationBufferMemory(memory_key="chat_history", input_key="human_input")
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

    docsearch = Pinecone.from_existing_index(
        index_name=PINECONE_INDEX_NAME, embedding= embeddings
    )

    docs = docsearch.similarity_search(query, k=8, filter={'assistant': '1'})
    print(docs)
    chat_openai = ChatOpenAI(temperature = 0.7, model = "gpt-4", openai_api_key = OPENAI_API_KEY)

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
    pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
    if index_name not in pinecone.list_indexes():
        pinecone.create_index(index_name, dimension=dimension)
    return pinecone.Index(index_name)

# Storing and Retrieving Embeddings with Pinecone
def store_embeddings_in_pinecone(chunks, metalist):
    try:
        pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        Pinecone.from_texts(
            chunks, embeddings, 
                index_name=PINECONE_INDEX_NAME, metadatas = metalist)
        print("Success embedding...")

    except Exception as e:
        print("Error embedding...", str(e))

def retrieve_embeddings_from_pinecone(index_name, query_embedding):
    pinecone = Pinecone(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
    vector_store = pinecone.index(index_name)
    results = vector_store.query(queries=query_embedding)
    return results

# Delete all records of the index
def del_all_records():
    try:
        index.delete(delete_all=True)
        return True
    except:
        return False

def del_knowledgebase_by_assistant_id(assistant_id):
    try :
        index.delete(
            filter={
                'assistant':1,
                'knowledge':1
            }
        )
        print('Deleted assistant ', assistant_id)
        return True
    except :
        return False

def del_knowledge_by_knowledge_id(knowledge_id):
    try:
        index.delete(
            filter={
                'knowledge':knowledge_id
            }
        )
        return True
    except:
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

def query_with_dolt(query):
    # sql_db = SQLDatabase.from_dbapi(db)
    db = SQLDatabase.from_uri(f"mysql+mysqldb://{DOLT_USERNAME}:{DOLT_PASSWORD}@{DOLT_HOST}/{DOLT_DATABASE}?ssl=1")
    tookkit = SQLDatabaseToolkit(db=db, llm=OpenAI(temperature=0))
    agent_executor = create_sql_agent(
        llm=OpenAI(temperature=0),
        toolkit=tookkit,
        verbose=True,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    )

    res = agent_executor.run(query)
    # print(res)
    return res





