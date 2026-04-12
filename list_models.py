import requests
import os
from dotenv import load_dotenv

load_dotenv()
key = os.environ.get("GEMINI_API_KEY")

def list_models():
    # Listando modelos disponíveis v1beta
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    r = requests.get(url)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")

if __name__ == "__main__":
    list_models()
