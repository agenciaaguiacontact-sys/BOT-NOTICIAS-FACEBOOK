import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

FB_TOKEN = os.environ.get("FB_TOKEN")
TARGET_PAGE_ID = os.environ.get("FB_PAGE_ID")
FB_GRAPH = "https://graph.facebook.com/v25.0"

def resolver_page_token():
    print(f"--- RESOLVENDO TOKEN DE PÁGINA ---")
    if not FB_TOKEN:
        print("Erro: FB_TOKEN não encontrado.")
        return

    url = f"{FB_GRAPH}/me/accounts?access_token={FB_TOKEN}"
    try:
        r = requests.get(url)
        data = r.json()
        
        if "error" in data:
            print(f"Erro na API: {data['error'].get('message')}")
            return

        pages = data.get("data", [])
        if not pages:
            print("Nenhuma página encontrada para este usuário.")
            return

        print(f"Encontradas {len(pages)} páginas.")
        for page in pages:
            p_id = page.get("id")
            p_name = page.get("name")
            p_token = page.get("access_token")
            
            print(f"- Página: {p_name} (ID: {p_id})")
            
            if p_id == TARGET_PAGE_ID:
                print(f"\nSUCESSO! Encontrei a pagina alvo: {p_name}")
                with open("found_token.txt", "w") as f:
                    f.write(p_token)
                print(f"O TOKEN FOI SALVO EM: found_token.txt")
                return

        print(f"\n⚠️ PÁGINA COM ID {TARGET_PAGE_ID} NÃO ENCONTRADA NA LISTA.")
        print("Páginas disponíveis:")
        for page in pages:
            print(f"  {page.get('name')} (ID: {page.get('id')})")

    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    resolver_page_token()
