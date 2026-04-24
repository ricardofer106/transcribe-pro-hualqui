import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("VITE_GEMINI_API_KEY")
if not api_key:
    print("API Key not found")
    exit()

client = genai.Client(api_key=api_key)

print("Listing models...")
try:
    for model in client.models.list():
        print(f"Model: {model.name}")
except Exception as e:
    print(f"Error listing models: {e}")
