import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)
FB_PAGE_ID = os.environ.get("FB_PAGE_ID", "").strip()
FB_TOKEN   = os.environ.get("FB_TOKEN", "").strip()
FB_GRAPH   = "https://graph.facebook.com/v22.0"

r = requests.get(
    f"{FB_GRAPH}/{FB_PAGE_ID}/posts",
    params={"fields": "id,message,created_time,permalink_url", "limit": 3, "access_token": FB_TOKEN},
    timeout=15
)
data = r.json()
if "data" in data:
    for p in data["data"]:
        print(f"ID    : {p.get('id')}")
        print(f"Hora  : {p.get('created_time')}")
        print(f"Link  : {p.get('permalink_url', 'N/A')}")
        print(f"Msg   : {str(p.get('message',''))[:100]}")
        print("---")
else:
    print("Erro ou sem posts:", data)
