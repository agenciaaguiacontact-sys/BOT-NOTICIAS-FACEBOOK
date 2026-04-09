import os
import requests
import webbrowser
from dotenv import load_dotenv

# Carrega configurações
load_dotenv(override=True)

FB_PAGE_ID = os.environ.get("FB_PAGE_ID", "SEU_ID_DA_PAGINA")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
FB_TOKEN = os.environ.get("FB_TOKEN", "")

def gerar_link_token():
    # Escopos necessários para o bot funcionar em 2025
    scopes = [
        "pages_manage_engagement", 
        "pages_read_engagement", 
        "pages_show_list", 
        "business_management",
        "public_profile"
    ]
    scope_str = ",".join(scopes)
    
    url = f"https://developers.facebook.com/tools/explorer/?method=GET&path={FB_PAGE_ID}%3Ffields%3Did%2Cname&version=v20.0&scope={scope_str}"
    
    print("\n" + "="*50)
    print("🚀 ASSISTENTE DE CONFIGURAÇÃO - REELS BOT FINAL")
    print("="*50)
    print("\n1. RENOVAÇÃO DE TOKEN FACEBOOK:")
    print(f"Clique no link abaixo para gerar um novo token com todas as permissões necessárias:")
    print(f"\n👉 {url}")
    print("\n(Selecione seu App 'Reels Bot Final' e sua Página 'Aconteceu Hoje' no menu da direita)")

def validar_env():
    print("\n" + "-"*30)
    print("📋 STATUS DO AMBIENTE (.env):")
    
    # Valida Gemini
    if not GEMINI_KEY:
        print("🔴 GEMINI_API_KEY: Ausente!")
    else:
        url_gemini = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro?key={GEMINI_KEY}"
        try:
            r = requests.get(url_gemini, timeout=5)
            if r.status_code == 200:
                print("🟢 GEMINI_API_KEY: Válida!")
            else:
                print(f"🔴 GEMINI_API_KEY: Inválida (Erro {r.status_code})")
        except:
            print("🔴 GEMINI_API_KEY: Erro de Conexão")

    # Valida Meta
    if not FB_TOKEN:
        print("🔴 FB_TOKEN: Ausente!")
    else:
        url_fb = f"https://graph.facebook.com/v20.0/me?access_token={FB_TOKEN}"
        try:
            r = requests.get(url_fb, timeout=5)
            if r.status_code == 200:
                print(f"🟢 FB_TOKEN: Válido! (Autenticado como: {r.json().get('name')})")
            else:
                print(f"🔴 FB_TOKEN: Inválido ou Expirado (Erro {r.status_code})")
        except:
            print("🔴 FB_TOKEN: Erro de Conexão")

    print("="*50)

if __name__ == "__main__":
    gerar_link_token()
    validar_env()
    print("\n💡 DICA: Para o erro #200 (Comentários), certifique-se de que mudou para 'Acesso Avançado'")
    print("na permissão 'pages_manage_engagement' no painel Meta Developers.")
