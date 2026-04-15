from google import genai
from dotenv import load_dotenv
import os

load_dotenv("../.env")
api_key = os.getenv("GEMINI_API_KEY")

print(f"Testing with API Key: {api_key[:10]}..." if api_key else "No API Key found")

try:
    client = genai.Client(api_key=api_key)
    for m in client.models.list():
        if 'flash' in m.name.lower():
            print(f"Model ID: {m.name}")
except Exception as e:
    print(f"Error: {e}")
