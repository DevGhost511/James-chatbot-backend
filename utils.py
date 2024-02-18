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
    
def generate_kb_from_xlsx(assistant_id, knowledge_id, path, api_key, index_name):
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
    ids = []
    
    for c in enumerate(chunks):
        metalist.append(metadic)
        ids.append(str(knowledge_id))

    store_embeddings_in_pinecone(chunks, metalist, api_key, ids, index_name)
    return len(chunks)

def generate_kb_from_file(assistant_id, knowledge_id, path, api_key, index_name):
    try:
        extension = path.split('.')[-1]
        extension = extension.lower()
        if extension == 'txt':
            count = generate_kb_from_txt(assistant_id=assistant_id, knowledge_id=knowledge_id, path=path, api_key=api_key, index_name=index_name)
            os.remove(path)
            return count
        if extension == 'xlsx' or extension == 'xls':
            count = generate_kb_from_xlsx(assistant_id, knowledge_id, path, api_key=api_key, index_name=index_name)
            os.remove(path)
            return count
        return -1
    except Exception as e:
        print(str(e))
        return -1

def generate_kb_from_txt(assistant_id, knowledge_id, path, api_key, index_name):
    try:
        with open(path, encoding='utf8') as f:
            content = f.read()
        chunks = tiktoken_split(content)
        metadic ={'knowledge':knowledge_id, 'assistant':assistant_id}
        metalist = []
        ids = []
        for index, chunk in enumerate(chunks):
            metalist.append(metadic)
            ids.append(str(knowledge_id)+"_"+str(index))

        store_embeddings_in_pinecone(chunks, metalist, api_key, ids, index_name)
        return len(chunks)
    except Exception as e:
        print(str(e))
        return -1

def generate_kb_from_url(assistant_id, knowledge_id, url, api_key, index_name):
    try:
        chunks = get_chunks(url)
        if chunks is None:
            return False
        metadic ={'knowledge':knowledge_id, 'assistant':assistant_id}
        print(chunks)
        metalist = []
        ids = []
        for index, chunk in enumerate(chunks):
            metalist.append(metadic)
            ids.append(str(knowledge_id)+"_"+str(index))
        store_embeddings_in_pinecone(chunks, metalist, api_key, ids, index_name)
        return len(chunks)
    except Exception as e:
        print(str(e))
        return -1

def get_response(query, prompt, latest_records, assistant_id):
    
    end = """
    Context:{context}
    Chat history:{chat_history}
    Human: {human_input}
    Assistant:"""
    template = prompt + end
    answer = generate_answer(query=query, assistant_id=assistant_id, latest_records=latest_records, template=template)
    
    return answer

def query_without_knowledge(chat_history, user_query):
    template = """The following is a friendly conversation between a human and an AI. The AI is talkative and provides lots of specific details from its context. If the AI does not know the answer to a question, it truthfully says it does not know.
        Context:{context}
        Chat history:{chat_history}
        Human: {human_input}
        AI:"""
    
    return ""
