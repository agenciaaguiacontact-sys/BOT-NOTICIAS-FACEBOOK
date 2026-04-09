import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

USER_TOKEN = os.environ.get("FB_USER_TOKEN")
PAGE_ID = os.environ.get("FB_PAGE_ID")

if not USER_TOKEN:
    print("USER_TOKEN não encontrado no .env")
else:
    url = f"https://graph.facebook.com/v22.0/me/accounts?access_token={USER_TOKEN}"
    r = requests.get(url)
    data = r.json()
    if "data" in data:
        for page in data["data"]:
            if page["id"] == PAGE_ID:
                print(f"NOVO_TOKEN={page['access_token']}")
                exit(0)
        print("Página não encontrada nas contas do usuário.")
    else:
        print(f"Erro ao obter contas: {data}")
