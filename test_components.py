import os
import requests
import json
import logging
from dotenv import load_dotenv

# Configurações de log
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("VERIFIER")

load_dotenv(override=True)

# Configurações do .env
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
FB_TOKEN = os.environ.get("FB_TOKEN")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")
SFY_EMAIL = os.environ.get("SFY_EMAIL")
SFY_PASSWORD = os.environ.get("SFY_PASSWORD")

def test_gemini():
    log.info("--- TESTANDO GEMINI AI ---")
    if not GEMINI_KEY:
        log.error("GEMINI_API_KEY não encontrada.")
        return False
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    payload = {"contents":[{"parts":[{"text":"Escreva um título de 3 palavras para uma notícia sobre IA."}]}]}
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code == 200:
            res = r.json()
            texto = res["candidates"][0]["content"]["parts"][0]["text"].strip()
            log.info(f"✅ Gemini OK! Resposta: {texto}")
            return True
        else:
            log.error(f"❌ Erro Gemini {r.status_code}: {r.text}")
            return False
    except Exception as e:
        log.error(f"❌ Exceção Gemini: {e}")
        return False

def test_meta_comment():
    log.info("--- TESTANDO META GRAPH API (COMMENTS) ---")
    if not FB_TOKEN or not FB_PAGE_ID:
        log.error("FB_TOKEN ou FB_PAGE_ID não encontrados.")
        return False
    
    # 1. Tenta pegar o último post da página
    url_posts = f"https://graph.facebook.com/v25.0/{FB_PAGE_ID}/published_posts?limit=1&access_token={FB_TOKEN}"
    try:
        r = requests.get(url_posts)
        data = r.json()
        if "data" in data and len(data["data"]) > 0:
            last_post_id = data["data"][0]["id"]
            log.info(f"Último post encontrado: {last_post_id}")
            
            # 2. Tenta ler os comentários do post (teste de leitura)
            url_read = f"https://graph.facebook.com/v25.0/{last_post_id}/comments?access_token={FB_TOKEN}"
            r_read = requests.get(url_read)
            if r_read.status_code == 200:
                log.info("✅ Leitura de posts/comentários OK.")
            else:
                log.warning(f"⚠️ Erro ao ler comentários (pode ser restrição de nível de acesso): {r_read.text}")

            # 3. Tenta postar um comentário de diagnóstico
            log.info("Tentando inserir comentário de diagnóstico...")
            url_comment = f"https://graph.facebook.com/v25.0/{last_post_id}/comments"
            payload = {"message": "🔍 Verificação técnica: Sistema de automação operando. (Teste Interno)", "access_token": FB_TOKEN}
            r_post = requests.post(url_comment, data=payload)
            
            if r_post.status_code == 200:
                log.info("✅ SUCESSO! O comentário foi postado com sucesso.")
                return True
            else:
                log.error(f"❌ FALHA NO COMENTÁRIO: {r_post.text}")
                return False
        else:
            log.warning("Nenhum post encontrado na página.")
            return False
    except Exception as e:
        log.error(f"❌ Exceção Meta: {e}")
        return False

def main():
    results = {
        "Gemini": test_gemini(),
        "Meta_Comments": test_meta_comment()
    }
    
    print("\n" + "="*30)
    print("RESULTADOS DA VERIFICAÇÃO")
    print("="*30)
    for k, v in results.items():
        status = "🟢 FUNCIONAL" if v else "🔴 BLOQUEADO/ERRO"
        print(f"{k:15}: {status}")
    print("="*30)

if __name__ == "__main__":
    main()
