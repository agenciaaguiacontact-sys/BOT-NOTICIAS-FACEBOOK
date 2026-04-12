import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
key = os.environ.get("GEMINI_API_KEY")

def test():
    # Testando v1beta com gemini-1.5-flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
    payload = {
        "contents": [{
            "parts": [{"text": "Diga apenas a palavra TESTE"}]
        }]
    }
    headers = {'Content-Type': 'application/json'}
    r = requests.post(url, json=payload, headers=headers)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")

if __name__ == "__main__":
    test()
