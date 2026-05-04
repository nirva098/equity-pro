import os
from dotenv import load_dotenv
import requests

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
response = requests.get(url)

print("Status:", response.status_code)
if response.status_code == 200:
    data = response.json()
    models = [m['name'] for m in data.get('models', [])]
    print("Available models:")
    for m in models:
        print(f" - {m}")
else:
    print("Error:", response.text)
