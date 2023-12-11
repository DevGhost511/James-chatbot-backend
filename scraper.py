import requests
from bs4 import BeautifulSoup
from langchain.document_loaders import BSHTMLLoader
from chunker import tiktoken_split

# Define a function to scrape the text content from a URL
def scrape_url(url):
    try:
        # Send a GET request to the URL
        response = requests.get(url)
        
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
            
        
        # Extract the relevant text content from the HTML
        text = soup.get_text()
        # Preprocess the text content as needed
        processed_text = preprocess_text(text)
    
        return processed_text
    except :
        return False

# Define a function to preprocess the extracted text content
def preprocess_text(text):
    # Clean the text by removing unwanted characters and symbols
    cleaned_text = text.replace('\n', ' ').replace('\r', '').strip()
    return cleaned_text


# Scrape the text content from each URL and store it in a list
def scrape_urls(urls):    
    # Scrape the text content from each URL
    scraped_data = []
    try:
        for url in urls:
            scraped_text = scrape_url(url)
            if scraped_text is False:
                return False
            scraped_data.append(scraped_text)
        return scraped_data
    except:
        return False

def get_chunks(urls):
    chunks = []
    try:
        for data in scrape_urls(urls):
            chunks.extend(tiktoken_split(data))
        # print("Scraped chunks >>>", chunks)
        return chunks
    except:
        return False





