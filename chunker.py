import tiktoken
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Pinecone

from langchain.embeddings.openai import OpenAIEmbeddings
import os
from dotenv import load_dotenv

load_dotenv()
tokenizer = tiktoken.get_encoding('cl100k_base')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
print("Openai---->",OPENAI_API_KEY)
def tiktoken_len(text):
    tokens = tokenizer.encode(
        text,
        disallowed_special=()
    )
    return len(tokens)

def tiktoken_split(text):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=20,
        length_function=tiktoken_len,
        separators=['\n\n', '\n', ' ', '']
    )
    chunks = splitter.split_text(text)

    return chunks

def getPineconeFromIndex(index_name):
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

    docsearch = Pinecone.from_existing_index(
        index_name=index_name, embedding= embeddings
    )
    return docsearch

def saveToPinecone(chunks, embeddings, index_name, metalist, ids):
    print("Ids---->", ids)
    
    Pinecone.from_texts(chunks, index_name= index_name, embedding=embeddings, metadatas = metalist, ids = ids)
    
    print("Success embedding...")


    