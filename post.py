import requests
import logging
from openai import OpenAI
import os
import schedule
import time
from dotenv import load_dotenv
import random

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

api_key = os.getenv('OPENAI_API_KEY')
LT_LONG_TOKEN = os.getenv('LT_LONG_TOKEN')
STORMGLASS_API_KEY = "76916c28-f3b2-11ed-8d52-0242ac130002-76916d04-f3b2-11ed-8d52-0242ac130002"  # Replace with your StormGlass API key

if not api_key or not LT_LONG_TOKEN:
    raise ValueError("Environment variables for OpenAI API key or Facebook/Instagram long-lived access token are missing.")

client = OpenAI(api_key=api_key)

page_id = '192229940650983'
ig_user_id = '17841460703039794'

def fetch_surf_conditions(api_key, latitude, longitude):
    url = "https://api.stormglass.io/v2/weather/point"
    params = {
        'lat': latitude,
        'lng': longitude,
        'params': ','.join(['waveHeight', 'waterTemperature', 'windSpeed', 'windDirection']),
    }
    headers = {
        'Authorization': api_key
    }
    
    logging.info(f"Sending request to StormGlass: URL={url}, Params={params}")
    response = requests.get(url, params=params, headers=headers)
    
    if response.status_code == 200:
        logging.info(f"Received response from StormGlass: {response.json()}")
        return response.json()
    else:
        logging.error(f"Failed to fetch data from StormGlass, Status Code={response.status_code}, Response={response.text}")
        return {'error': 'Failed to fetch data', 'status_code': response.status_code}

def get_lat_long_for_beach(beach_name):
    prompt = f"Provide the latitude and longitude for {beach_name} beach. Only respond in a format like this nothing else:34.0195, -118.4912"
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a geographical information system. Provide accurate data."},
                {"role": "user", "content": prompt}
            ]
        )
        lat_long_response = response.choices[0].message.content
        logging.info("Latitude and Longitude Response:\n%s", lat_long_response)
        # Example parsing, you might need to adjust based on the response format
        lat_long = lat_long_response.split(',')
        latitude = lat_long[0].strip()
        longitude = lat_long[1].strip()
        return latitude, longitude
    except Exception as e:
        logging.error("Failed to get latitude and longitude: %s", e)
        return None, None

def generate_surfing_content():
    try:
        with open('beaches.txt', 'r') as file:
            beaches = file.readlines()
            beach = random.choice(beaches).strip()
    except FileNotFoundError:
        logging.error("beach.txt file not found.")
        return None, None
    except Exception as e:
        logging.error("Failed to read from beach.txt: %s", e)
        return None, None

    latitude, longitude = get_lat_long_for_beach(beach)
    if latitude and longitude:
        surf_conditions = fetch_surf_conditions(STORMGLASS_API_KEY, latitude, longitude)
        if 'error' not in surf_conditions:
            conditions_str = f"Wave Height: {surf_conditions['hours'][0]['waveHeight']['noaa']}m, Water Temperature: {surf_conditions['hours'][0]['waterTemperature']['noaa']}C, Wind Speed: {surf_conditions['hours'][0]['windSpeed']['noaa']}m/s, Wind Direction: {surf_conditions['hours'][0]['windDirection']['noaa']} degrees"
        else:
            conditions_str = "No conditions available"
    else:
        conditions_str = "No conditions available"

    surf_prompt = f"Write a facebook post update for the local surfers. You are a local surf expert at {beach}, considering the current wave conditions, select what size/type of board would be best for these conditions, and provide local tips for surfers based on the following conditions: {conditions_str}. Come up with other tips to say. Only say nice things about the local only if you mention them."
    
    try:
        logging.info("Generating surfing content")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an old school surfer lingo talking knowledgeable surfing guide. Don't give newbie lessons"},
                {"role": "user", "content": surf_prompt}
            ]
        )
        surf_instructions = response.choices[0].message.content
        logging.info("Generated Surfing Content:\n%s", surf_instructions)
        return surf_instructions, beach
    except Exception as e:
        logging.error("Failed to generate surfing content: %s", e)
        return None, None

def generate_hashtags(surf_instructions):
    hashtag_prompt = f"Based on the following content, generate relevant hashtags: {surf_instructions}"
    
    try:
        logging.info("Generating hashtags")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a social media expert. Generate relevant hashtags based on the content."},
                {"role": "user", "content": hashtag_prompt}
            ]
        )
        hashtags = response.choices[0].message.content
        logging.info("Generated Hashtags:\n%s", hashtags)
        return hashtags
    except Exception as e:
        logging.error("Failed to generate hashtags: %s", e)
        return None

def generate_surfing_image(surf_instructions, beach):
    image_prompt = f"Real Photo of someone surfing the best wave at {beach}. Put someone at this location, on a wave, and on this board doing this surf style. make sure the physics of the surfer angle based on the wave is correct positioning, human photo realistic. No words or text"
    
    try:
        logging.info("Generating surfing image with prompt: %s", image_prompt)
        response = client.images.generate(
            model="dall-e-3",
            prompt=image_prompt,
            size="1024x1024",
            n=1,
        )
        image_url = response.data[0].url
        logging.info("Generated Surfing Image URL: %s", image_url)

        return image_url
    except Exception as e:
        logging.error("Failed to generate surfing image: %s", e)
        return None

def generate_content_and_post():
    logging.info("Starting surfing content generation and posting process")
    
    try:
        surf_instructions, beach = generate_surfing_content()  # This returns both surf_instructions and beach
        if surf_instructions and beach:
            hashtags = generate_hashtags(surf_instructions)
            image_url = generate_surfing_image(surf_instructions, beach)  # Make sure to pass both arguments here
            if image_url:
                try:
                    logging.info("Posting to Facebook and Instagram")
                    publish_photo_with_message(page_id, ig_user_id, surf_instructions, image_url, hashtags)
                except Exception as e:
                    logging.error("Failed to post to Facebook or Instagram: %s", e)
    except Exception as e:
        logging.error("An error occurred during content generation or posting: %s", e)

def publish_photo_with_message(page_id, ig_user_id, message, photo_url, hashtags):
    # Combine message and hashtags for posting
    full_message = f"{message}\n\n{hashtags}"
    
    # Upload photo to Facebook with published set to false for story
    try:
        fb_photo_upload_url = f"https://graph.facebook.com/{page_id}/photos"
        fb_photo_upload_payload = {
            'url': photo_url,
            'caption': full_message,
            'published': 'false',
            'access_token': LT_LONG_TOKEN
        }
        fb_photo_upload_response = requests.post(fb_photo_upload_url, data=fb_photo_upload_payload)
        if fb_photo_upload_response.status_code == 200:
            photo_id = fb_photo_upload_response.json().get('id')
            logging.info("Successfully uploaded photo to Facebook for story: %s", fb_photo_upload_response.json())
            
            # Publish a photo story on Facebook
            fb_photo_story_url = f"https://graph.facebook.com/{page_id}/photo_stories"
            fb_photo_story_payload = {
                'photo_id': photo_id,
                'access_token': LT_LONG_TOKEN
            }
            fb_photo_story_response = requests.post(fb_photo_story_url, data=fb_photo_story_payload)
            if fb_photo_story_response.status_code == 200:
                logging.info("Successfully published photo story to Facebook: %s", fb_photo_story_response.json())
            else:
                logging.error("Failed to publish photo story to Facebook. Response: %s", fb_photo_story_response.text)
        else:
            logging.error("Failed to upload photo to Facebook for story. Response: %s", fb_photo_upload_response.text)
    except Exception as e:
        logging.error("Exception occurred while uploading photo or publishing photo story to Facebook: %s", e)

    # Post to Facebook profile
    try:
        fb_profile_url = f"https://graph.facebook.com/{page_id}/photos"
        fb_profile_payload = {
            'url': photo_url,
            'caption': full_message,
            'access_token': LT_LONG_TOKEN
        }
        fb_profile_response = requests.post(fb_profile_url, data=fb_profile_payload)
        if fb_profile_response.status_code == 200:
            logging.info("Successfully published to Facebook profile: %s", fb_profile_response.json())
        else:
            logging.error("Failed to publish to Facebook profile. Response: %s", fb_profile_response.text)
    except Exception as e:
        logging.error("Exception occurred while posting to Facebook profile: %s", e)

    # Create a media container on Instagram for feed
    try:
        ig_media_url = f"https://graph.facebook.com/v10.0/{ig_user_id}/media"
        ig_media_payload = {
            'image_url': photo_url,
            'caption': full_message,
            'access_token': LT_LONG_TOKEN
        }
        ig_media_response = requests.post(ig_media_url, data=ig_media_payload)
        logging.info(f"Instagram media container creation response: {ig_media_response.json()}")
        if ig_media_response.status_code == 200:
            ig_media_id = ig_media_response.json().get('id')
            logging.info("Successfully created Instagram media container for feed.")
            
            # Publish the media container to Instagram feed
            ig_publish_url = f"https://graph.facebook.com/v10.0/{ig_user_id}/media_publish"
            ig_publish_payload = {
                'creation_id': ig_media_id,
                'access_token': LT_LONG_TOKEN
            }
            ig_publish_response = requests.post(ig_publish_url, data=ig_publish_payload)
            logging.info(f"Instagram feed publish response: {ig_publish_response.json()}")
            if ig_publish_response.status_code == 200:
                logging.info("Successfully published to Instagram feed.")
            else:
                logging.error("Failed to publish to Instagram feed.")
        else:
            logging.error("Failed to create Instagram media container for feed.")
    except Exception as e:
        logging.error(f"Exception occurred while posting to Instagram feed: {e}")
        
    # Create a media container on Instagram for story
    try:
        ig_story_media_url = f"https://graph.facebook.com/v10.0/{ig_user_id}/media"
        ig_story_media_payload = {
            'image_url': photo_url,
            'caption': full_message,
            'access_token': LT_LONG_TOKEN,
            'media_type': 'STORIES'  # Corrected parameter for story media type
        }
        ig_story_media_response = requests.post(ig_story_media_url, data=ig_story_media_payload)
        logging.info(f"Instagram story media container creation response: {ig_story_media_response.json()}")
        if ig_story_media_response.status_code == 200:
            ig_story_media_id = ig_story_media_response.json().get('id')
            logging.info("Successfully created Instagram media container for story.")
            
            # Publish the media container to Instagram story
            ig_story_publish_url = f"https://graph.facebook.com/v10.0/{ig_user_id}/media_publish"
            ig_story_publish_payload = {
                'creation_id': ig_story_media_id,
                'access_token': LT_LONG_TOKEN
            }
            ig_story_publish_response = requests.post(ig_story_publish_url, data=ig_story_publish_payload)
            logging.info(f"Instagram story publish response: {ig_story_publish_response.json()}")
            if ig_story_publish_response.status_code == 200:
                logging.info("Successfully published to Instagram story.")
            else:
                logging.error("Failed to publish to Instagram story.")
        else:
            logging.error("Failed to create Instagram media container for story.")
    except Exception as e:
        logging.error(f"Exception occurred while posting to Instagram story: {e}")



generate_content_and_post()

# Adjust the schedule as needed
schedule.every(1).hour.do(generate_content_and_post)  # For demonstration, adjust as needed

while True:
    schedule.run_pending()
    time.sleep(1)