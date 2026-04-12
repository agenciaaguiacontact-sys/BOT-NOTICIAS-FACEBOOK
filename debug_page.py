import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

def diag():
    page_id = os.environ.get("FB_PAGE_ID")
    token = os.environ.get("FB_TOKEN")
    
    print(f"ID configurado: {page_id}")
    
    if not page_id or not token:
        print("Erro: FB_PAGE_ID ou FB_TOKEN não encontrados no .env")
        return

    url = f"https://graph.facebook.com/v22.0/{page_id}?fields=name&access_token={token}"
    try:
        r = requests.get(url)
        data = r.json()
        print(f"Resposta da API: {data}")
        nome = data.get("name")
        if nome:
            print(f"NOME DA PÁGINA: {nome}")
        else:
            print("Não foi possível obter o nome da página. Verifique o token.")
    except Exception as e:
        print(f"Erro na conexão: {e}")

if __name__ == "__main__":
    diag()
