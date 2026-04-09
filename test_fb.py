import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

FB_PAGE_ID = os.environ.get("FB_PAGE_ID")
FB_TOKEN = os.environ.get("FB_TOKEN")

url = f"https://graph.facebook.com/v22.0/{FB_PAGE_ID}?fields=name&access_token={FB_TOKEN}"
r = requests.get(url)
print(f"Status: {r.status_code}")
print(f"Response: {r.text}")
