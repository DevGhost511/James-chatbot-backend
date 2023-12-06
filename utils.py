from vectorizor import query_refiner
from scraper import get_chunks
from vectorizor import store_embeddings_in_pinecone
from vectorizor import generate_answer
import pandas
import simplejson as json
import openpyxl as xl 
from chunker import tiktoken_split

def generate_query(user_id, knowledge_name, chat_history, user_query):
    template = """The following is a friendly conversation between a human and an AI. The AI is talkative and provides lots of specific details from its context. If the AI does not know the answer to a question, it truthfully says it does not know. If there is no conversation history, plz provide proper answer automatically based on the query.
        Context:{context}
        Chat history:{chat_history}
        Human: {human_input}
        AI:"""
    print("Get query....")
    answer = generate_answer(query=user_query, user_id = user_id, knowledge_name=knowledge_name, latest_records=chat_history, template=template)

    return answer
    
def generate_kb():
    excel = xl.load_workbook("hospital cash price.xlsx")
    sheetnames = excel.sheetnames
    res = {}
    for sheetname in sheetnames:
        data = pandas.read_excel("hospital cash price.xlsx", sheet_name=sheetname)
        json_data = data.to_json()
        res.update({sheetname: json_data})
    str_data = json.dumps(res)
    chunks = tiktoken_split(str_data)
    metadic ={'source':'test'}
    metalist = []
    for c in enumerate(chunks):
        metalist.append(metadic)

    store_embeddings_in_pinecone(chunks, metalist)
    return res



def get_response(query):
    template = """The following is a friendly conversation between a human and an AI. The AI is talkative and provides lots of specific details from its context. If the AI does not know the answer to a question, it truthfully says it does not know. If there is no conversation history, plz provide proper answer automatically based on the query.
        Context:{context}
        Chat history:{chat_history}
        Human: {human_input}
        AI:"""
    answer = generate_answer(query=query, user_id = 'te', knowledge_name='st', latest_records=[], template=template)
    
    return ''

def save_to_pinecone(user_id, knowledge_name, knowledge_urls):
    metadic ={'source': user_id + knowledge_name}
    chunks = get_chunks(knowledge_urls)
    metalist = []
    for c in enumerate(chunks):
        metalist.append(metadic)
    store_embeddings_in_pinecone(chunks, metalist)

def query_without_knowledge(chat_history, user_query):
    template = """The following is a friendly conversation between a human and an AI. The AI is talkative and provides lots of specific details from its context. If the AI does not know the answer to a question, it truthfully says it does not know.
        Context:{context}
        Chat history:{chat_history}
        Human: {human_input}
        AI:"""
    
    return ""

    

    
    
    