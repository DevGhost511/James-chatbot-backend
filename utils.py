from vectorizor import query_refiner
from scraper import get_chunks
from vectorizor import store_embeddings_in_pinecone
from vectorizor import generate_answer
import pandas
import os
import simplejson as json
import openpyxl as xl 
from chunker import tiktoken_split

def generate_query(user_id, knowledge_name, chat_history, user_query):
    template = """
    The following is a friendly conversation between a human and an AI. The AI is talkative and provides lots of specific details from its context. If the AI does not know the answer to a question, it truthfully says it does not know current information but provides the latest information. If there is no conversation history, plz provide proper answer automatically based on the query.
    The response must be less than 300 words.\n
    Knowledge Base:{context}\n
    Chat history: {chat_history}\n
    Human: {human_input}\n
    Your response as Chatbot:"""
    
    print("Get query....")
    answer = generate_answer(query=user_query, user_id = user_id, knowledge_name=knowledge_name, latest_records=chat_history, template=template)

    return answer
    
def generate_kb_from_xlsx(assistant_id, knowledge_id, path):
    excel = xl.load_workbook(path)
    sheetnames = excel.sheetnames
    res = {}
    for sheetname in sheetnames:
        data = pandas.read_excel("hospital cash price.xlsx", sheet_name=sheetname)
        json_data = data.to_json()
        res.update({sheetname: json_data})
    str_data = json.dumps(res)
    chunks = tiktoken_split(str_data)
    metadic ={'knowledge':knowledge_id, 'assistant':assistant_id}
    metalist = []
    for c in enumerate(chunks):
        metalist.append(metadic)

    store_embeddings_in_pinecone(chunks, metalist)
    return res

def generate_kb_from_file(assistant_id, knowledge_id, path):
    try:
        extension = path.split('.')[-1]
        extension = extension.lower()
        if extension == 'txt':
            generate_kb_from_txt(assistant_id=assistant_id, knowledge_name=knowledge_id, path=path)
            os.remove(path)
            return True
        if extension == 'xlsx' or extension == 'xls':
            generate_kb_from_xlsx(assistant_id, knowledge_id, path)
            os.remove(path)
            return True
        return False
    except Exception as e:
        print(str(e))
        return False

def generate_kb_from_txt(assistant_id, knowledge_name, path):
    try:
        with open(path, encoding='utf8') as f:
            content = f.read()
        chunks = tiktoken_split(content)
        metadic ={'knowledge':knowledge_name, 'assistant':assistant_id}
        metalist = []
        for c in enumerate(chunks):
            metalist.append(metadic)

        store_embeddings_in_pinecone(chunks, metalist)
        return True
    except Exception as e:
        print(str(e))
        return False

def generate_kb_from_url(assistant_id, knowledge_id, url):
    try:
        chunks = get_chunks(url)
        if chunks is False:
            return False
        metadic ={'knowledge':knowledge_id, 'assistant':assistant_id}
        print(chunks)
        metalist = []
        for c in enumerate(chunks):
            metalist.append(metadic)
        store_embeddings_in_pinecone(chunks, metalist)
        return True
    except Exception as e:
        print(str(e))
        return False

def get_response(query, latest_records, user_id, assistatnt_id):
    template = """The following is a friendly conversation between a human and an assistant. The assistant is talkative and provides lots of specific details from its context. If there is no related context, plz provide proper answer automatically based on the query.
        The response mush be less than 100 words.
        Context:{context}
        Chat history:{chat_history}
        Human: {human_input}
        Assistant:"""
    answer = generate_answer(query=query, user_id = user_id, knowledge_name=assistatnt_id, latest_records=latest_records, template=template)
    
    return answer

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
