import requests
import schedule
import time
import logging
from openai import OpenAI
import random

# Setup basic configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Hardcoded API key for OpenAI
api_key = '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'

# Initialize OpenAI client with the API key
client = OpenAI(api_key=api_key)

# Facebook Page details
page_id = '288361271766168'
access_token = 'EAAYlFUewjJIBO2r6IAWinh0tFEXLSKNaA5w3mE7BUmAK5LgaTMgkvt2JIZCeWYDb0McWxtivdQQhDgcHgE9ZCo1UN8SZCv1VDs1MCXxZC8eMzvDWZCgqxbieGALzhQBG5ZBVqKVR2jlCdGMXX6YNSalNRMtHUdeD4O07ZBZAiICNNebchuitQXK0laCXKWwHLc9PvImKZAIXXdtIP5wZDZD'

def generate_recipe_and_post():
    logging.info("Starting recipe and post generation process")

    # Read ingredients from file and select 3 random ones
    with open('ingredients.txt', 'r') as file:
        ingredients = file.readlines()
    selected_ingredients = random.sample(ingredients, 3)
    ingredients_text = ', '.join([ingredient.strip() for ingredient in selected_ingredients])

    recipe_prompt = "Create a random meal recipe that includes the following 3 ingredients: " + ingredients_text + ". Ignore the amount of the ingredient you decide. Only respond with the Recipe name and the recipe no text before or after except hashtags that may be popularly clicked."

    try:
        logging.info("Generating recipe with prompt")
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": recipe_prompt}
            ]
        )
        recipe_text = completion.choices[0].message.content
        logging.info("Generated Recipe:\n%s", recipe_text)
    except Exception as e:
        logging.error("Failed to generate recipe: %s", e)
        return

    descriptive_prompt = "Imagine you are making an image of this finished cooked meal next to a uniquely attractive chef (pick female or male random but consistent in the prompt you write and random hair color and random traits every time which equate. skin color etc, unique photo lighting, unique setting etc), respond with a prompt that would generate the image in a text to image generator that uses very descriptive terms."
    
    try:
        logging.info("Generating descriptive prompt for the image")
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a chef who returns recipe posts."},
                {"role": "user", "content": descriptive_prompt + " Recipe: " + recipe_text + " including camera and lighting and quality angles of variations and unique image locations. be descriptive like a photographer describing, no rustic"}
            ]
        )
        image_prompt = completion.choices[0].message.content
        logging.info("Generated Descriptive Prompt for Image:\n%s", image_prompt)
    except Exception as e:
        logging.error("Failed to generate descriptive prompt: %s", e)
        return

    try:
        logging.info("Generating image for the recipe")
        response = client.images.generate(
            model="dall-e-3",
            prompt=image_prompt,
            size="1024x1024",
            n=1,
        )
        image_url = response.data[0].url
        logging.info("Generated Image URL: %s", image_url)
    except Exception as e:
        logging.error("Failed to generate image: %s", e)
        return

    try:
        logging.info("Uploading photo to Facebook without publishing")
        photo_id = upload_photo_without_publishing(page_id, image_url, recipe_text)  # Pass recipe_text here
        if photo_id:
            logging.info("Publishing photo story with uploaded photo")
            publish_photo_story(page_id, photo_id)
            logging.info("Posting to Facebook")
            publish_photo_with_message(page_id, recipe_text, image_url)
    except Exception as e:
        logging.error("Failed to post to Facebook: %s", e)

def upload_photo_without_publishing(page_id, photo_url, caption):
    url = f"https://graph.facebook.com/{page_id}/photos"
    payload = {
        'url': photo_url,
        'published': 'false',
        'access_token': access_token,
        'caption': caption  # Use the passed caption here
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        photo_id = response.json().get('id')
        logging.info("Successfully uploaded photo without publishing. Photo ID: %s", photo_id)
        return photo_id
    else:
        logging.error("Failed to upload photo without publishing. Response: %s", response.text)
        return None

def publish_photo_story(page_id, photo_id):
    url = f"https://graph.facebook.com/{page_id}/photo_stories"
    payload = {
        'photo_id': photo_id,
        'access_token': access_token
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200 and response.json().get('success'):
        logging.info("Successfully published photo story. Response: %s", response.json())
    else:
        logging.error("Failed to publish photo story. Response: %s", response.text)

def publish_photo_with_message(page_id, message, photo_url):
    url = f"https://graph.facebook.com/{page_id}/photos"
    payload = {
        'url': photo_url,
        'caption': message,
        'access_token': access_token
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        logging.info("Successfully published to Facebook: %s", response.json())
    else:
        logging.error("Failed to publish to Facebook. Response: %s", response.text)

# Call the function immediately for initial execution
generate_recipe_and_post()

# Schedule the task to run every hour
schedule.every(1).hour.do(generate_recipe_and_post)

# Run the scheduler indefinitely
if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(1)  # Sleep for a minute to avoid excessive CPU usage