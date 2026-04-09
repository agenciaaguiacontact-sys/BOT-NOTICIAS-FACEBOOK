import os
import requests
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv(override=True)

FB_TOKEN = os.environ.get("FB_TOKEN")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")
FB_GRAPH = "https://graph.facebook.com/v25.0"

def debug_token():
    print("--- DIAGNÓSTICO DE TOKEN META ---")
    if not FB_TOKEN:
        print("Erro: FB_TOKEN não encontrado no .env")
        return

    # 1. Verificar informações básicas do token
    url_base = f"{FB_GRAPH}/me?access_token={FB_TOKEN}"
    print(f"Consultando informações básicas...")
    
    try:
        r = requests.get(url_base)
        data = r.json()
        
        if "error" in data:
            print(f"\nERRO NA API (Basico):")
            print(f"Mensagem: {data['error'].get('message')}")
            print(f"Codigo: {data['error'].get('code')}")
            return

        print(f"\nTOKEN VALIDO!")
        print(f"Nome associado: {data.get('name')}")
        print(f"ID: {data.get('id')}")

        # 2. Tentar ver permissões em uma chamada separada
        print(f"\nConsultando permissoes...")
        url_perms = f"{FB_GRAPH}/me/permissions?access_token={FB_TOKEN}"
        r_perms = requests.get(url_perms)
        data_perms = r_perms.json()

        if "error" in data_perms:
            print(f"Não foi possível ler permissoes diretamente: {data_perms['error'].get('message')}")
        else:
            permissions = data_perms.get("data", [])
            has_manage_engagement = False
            has_read_engagement = False
            for p in permissions:
                status = p.get("status")
                name = p.get("permission")
                print(f"- {name}: {status}")
                if name == "pages_manage_engagement" and status == "granted":
                    has_manage_engagement = True
                if name == "pages_read_engagement" and status == "granted":
                    has_read_engagement = True
            
            if not has_manage_engagement:
                print("\nAVISO: A permissao 'pages_manage_engagement' NAO esta presente.")
            else:
                print("\nOK: A permissao 'pages_manage_engagement' esta ok.")
            
            if not has_read_engagement:
                print("\nAVISO: A permissao 'pages_read_engagement' NAO esta presente.")
            else:
                print("\nOK: A permissao 'pages_read_engagement' esta ok.")

        # 2. Verificar se o token é de Página ou de Usuário
        # Se o ID de 'me' for igual ao FB_PAGE_ID, é um Page Token.
        if data.get('id') == FB_PAGE_ID:
            print("\nTipo de Token: PAGE ACCESS TOKEN (Correto para automação de página)")
        else:
            print("\nTipo de Token: USER ACCESS TOKEN (Pode causar problemas em automações de longa duração)")

    except Exception as e:
        print(f"\nExceção durante a requisição: {e}")

if __name__ == "__main__":
    debug_token()
