import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)
FB_PAGE_ID = os.environ.get("FB_PAGE_ID", "").strip()
FB_TOKEN   = os.environ.get("FB_TOKEN", "").strip()

r = requests.get(
    f"https://graph.facebook.com/v22.0/{FB_PAGE_ID}/posts",
    params={"fields": "id,permalink_url,created_time,message", "limit": 1, "access_token": FB_TOKEN},
    timeout=15
)
data = r.json()
if "data" in data and data["data"]:
    p = data["data"][0]
    resultado = f"""POST_ID: {p.get('id')}
LINK: {p.get('permalink_url', 'N/A')}
HORA: {p.get('created_time')}
MENSAGEM: {p.get('message', '')[:200]}
"""
    print(resultado)
    with open("ultimo_post.txt", "w", encoding="utf-8") as f:
        f.write(resultado)
    print("Salvo em ultimo_post.txt")
else:
    print("Erro:", data)
