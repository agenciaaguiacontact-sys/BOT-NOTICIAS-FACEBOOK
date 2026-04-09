import os
import sys
import requests
from dotenv import load_dotenv

# Carrega as variáveis do .env
load_dotenv(override=True)

# Configuração de encoding para evitar erros com emojis no Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

TOKEN_FILE = "persistent_tokens.json"

def load_persistent_tokens():
    """Carrega tokens do arquivo JSON se ele existir."""
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                import json
                return json.load(f)
        except:
            pass
    return {}

def auto_renew_meta_token():
    """
    Tenta renovar o token de usuário atual para um de longa duração (60 dias)
    e depois atualiza o token de página relacionado.
    """
    app_id = os.environ.get("FB_APP_ID")
    app_secret = os.environ.get("FB_APP_SECRET")
    user_token = os.environ.get("FB_USER_TOKEN")
    page_id = os.environ.get("FB_PAGE_ID")

    if not all([app_id, app_secret, user_token]):
        print("⚠️ [RENOVAÇÃO] Faltam credenciais no .env (FB_APP_ID, FB_APP_SECRET ou FB_USER_TOKEN).")
        return None

    print("🔄 [RENOVAÇÃO] Tentando renovar token de usuário para longa duração...")
    
    # 1. Trocar token curto por token de longa duração (60 dias)
    url_exchange = "https://graph.facebook.com/v22.0/oauth/access_token"
    params_exchange = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": user_token
    }
    
    try:
        r = requests.get(url_exchange, params=params_exchange)
        res = r.json()
        
        if "access_token" not in res:
            print(f"❌ [RENOVAÇÃO] Erro ao trocar token: {res.get('error', {}).get('message', 'Erro desconhecido')}")
            return None
        
        long_user_token = res["access_token"]
        print("✅ [RENOVAÇÃO] Token de usuário de longa duração obtido.")

        # 2. Obter o token de página (Page Token) usando o novo token de usuário
        url_accounts = f"https://graph.facebook.com/v22.0/me/accounts?access_token={long_user_token}"
        r_acc = requests.get(url_accounts)
        acc_data = r_acc.json()
        
        new_page_token = None
        if "data" in acc_data:
            for page in acc_data["data"]:
                if page["id"] == page_id:
                    new_page_token = page["access_token"]
                    break
        
        if not new_page_token:
            print(f"❌ [RENOVAÇÃO] Não foi possível encontrar a página {page_id} nas contas associadas.")
            return None

        print("✅ [RENOVAÇÃO] Novo Page Token obtido.")
        
        # 3. Atualizar o arquivo .env e o persistent_tokens.json
        tokens = {
            "FB_USER_TOKEN": long_user_token,
            "FB_TOKEN": new_page_token
        }
        
        update_env_file(tokens)
        
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            import json
            json.dump(tokens, f, indent=2)
        
        print(f"🎉 [RENOVAÇÃO] Arquivos .env e {TOKEN_FILE} atualizados!")
        return new_page_token

    except Exception as e:
        print(f"❌ [RENOVAÇÃO] Exceção: {e}")
        return None

def update_env_file(new_values):
    """Atualiza valores no arquivo .env preservando os demais."""
    env_path = ".env"
    if not os.path.exists(env_path):
        return
    
    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    for key, value in new_values.items():
        found = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                found = True
                break
        if not found:
            lines.append(f"{key}={value}\n")
            
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

if __name__ == "__main__":
    auto_renew_meta_token()
