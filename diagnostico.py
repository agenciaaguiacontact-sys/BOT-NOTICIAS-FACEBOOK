import os
import requests
from dotenv import load_dotenv

def test_config():
    print("--- DIAGNÓSTICO DE CONFIGURAÇÃO ---")
    load_dotenv(override=True)
    
    page_id = os.environ.get("FB_PAGE_ID")
    token = os.environ.get("FB_TOKEN")
    gemini = os.environ.get("GEMINI_API_KEY")
    
    # 1. Verificar Gemini
    if gemini:
        print("✅ Gemini API Key: Presente")
    else:
        print("❌ Gemini API Key: AUSENTE")

    # 2. Verificar Facebook
    if not page_id or not token:
        print("❌ Facebook Credentials: ID ou Token ausentes no .env")
        return

    print(f"🔍 Validando acesso à Página ID: {page_id}")
    url = f"https://graph.facebook.com/v22.0/{page_id}?fields=name&access_token={token}"
    
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        
        if "error" in data:
            print(f"❌ Erro Facebook API: {data['error'].get('message')}")
            if data['error'].get('code') == 190:
                print("   👉 O Token parece ter EXPIRADO ou é inválido.")
        else:
            nome = data.get("name")
            print(f"✅ Conexão OK! Nome da Página: {nome}")
            if nome == "Aconteceu Hoje":
                print("   🔒 Trava de Segurança: PASSOU")
            else:
                print(f"   ⚠️ ATENÇÃO: A página alvo ({nome}) não é a correta ('Aconteceu Hoje')")
                
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")

if __name__ == "__main__":
    test_config()
