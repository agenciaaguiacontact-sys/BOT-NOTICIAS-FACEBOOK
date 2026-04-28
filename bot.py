#!/usr/bin/env python3
"""
SharesForYou → Facebook Auto-Poster Bot
Versão FINAL ABSOLUTA - Noticiário Profissional
"""

import os
import json
import time
import logging
import hashlib
import textwrap
import requests
import random
import re
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv
import traceback

load_dotenv(override=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# Configurações
SFY_EMAIL    = os.environ.get("SFY_EMAIL", "")
SFY_PASSWORD = os.environ.get("SFY_PASSWORD", "")
FB_PAGE_ID   = os.environ.get("FB_PAGE_ID", "122181202022766925")
FB_TOKEN     = os.environ.get("FB_TOKEN", "")
GEMINI_KEY   = os.environ.get("GEMINI_API_KEY", "")

POSTED_FILE  = "posted_ids.json"
SFY_SHARE    = "https://www.sharesforyou.com/dashboard/share"
SFY_LOGIN    = "https://www.sharesforyou.com/login"
FB_GRAPH     = "https://graph.facebook.com/v22.0"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}



def make_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    r = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=r))
    return s

def load_posted():
    if os.path.exists(POSTED_FILE):
        try: return set(json.load(open(POSTED_FILE)))
        except: return set()
    return set()

def save_posted(ids):
    json.dump(sorted(list(ids))[-500:], open(POSTED_FILE, "w"), indent=2)

def make_article_id(url, title=""):
    # Remove query strings para evitar duplicatas por parâmetros de rastreio
    clean_url = url.split("?")[0].split("#")[0]
    # Normaliza o título para incluir no hash (evita duplicatas se a URL mudar mas o título for igual)
    title_norm = re.sub(r'[^\w]', '', title.lower())
    combined = f"{clean_url}|{title_norm}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]

RECENT_HOOKS_FILE = "recent_hooks.json"

def load_recent_hooks():
    if os.path.exists(RECENT_HOOKS_FILE):
        try:
            with open(RECENT_HOOKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return []
    # Fallback para o arquivo antigo caso exista
    if os.path.exists("last_title.txt"):
        try:
            t = open("last_title.txt", "r", encoding="utf-8").read().strip()
            return [t] if t else []
        except: return []
    return []

def save_new_hook(hook):
    hooks = load_recent_hooks()
    if hook in hooks:
        hooks.remove(hook)
    hooks.insert(0, hook)
    hooks = hooks[:20] # Mantém apenas os 20 últimos
    try:
        with open(RECENT_HOOKS_FILE, "w", encoding="utf-8") as f:
            json.dump(hooks, f, ensure_ascii=False, indent=2)
    except: pass

def baixar_fonte(emoji=False):
    # Priorizar fonte local para compatibilidade com Nuvem (Linux)
    local_impact = os.path.join("fonts", "impact.ttf")
    if os.path.exists(local_impact): return local_impact

    if emoji:
        for f in ["C:\\Windows\\Fonts\\seguiemj.ttf"]:
            if os.path.exists(f): return f
            
    # Fallbacks de sistema
    for f in ["C:\\Windows\\Fonts\\impact.ttf", "fonts/NotoSans-Bold.ttf", "C:\\Windows\\Fonts\\arialbd.ttf"]:
        if os.path.exists(f): return f
    return None

def limpar_emojis(texto):
    # Preserva caracteres acentuados e pontuação, removendo apenas o que não é texto 'humano'
    return re.sub(r'[^\w\s.,!?;:\"\'\(\)\-\u00C0-\u00FF]+', '', texto).strip()

def emoji_to_hex(emoji_char):
    """Converte um caractere emoji para sua representação hexadecimal (iamcal style)."""
    if not emoji_char: return None
    try:
        hex_parts = []
        for char in emoji_char:
            h = f"{ord(char):x}"
            if h != "fe0f": # Remove variation selector
                hex_parts.append(h)
        return "-".join(hex_parts)
    except:
        return None

def gerar_gancho(title):
    recent_hooks = load_recent_hooks()
    
    fallbacks = [
        {"hook": "REVELAÇÃO CHOCANTE!", "category": "URGENTE"},
        {"hook": "MUNDO EM CHOQUE!", "category": "URGENTE"},
        {"hook": "VOCÊ VIU ISSO?", "category": "URGENTE"},
        {"hook": "BOMBA DO DIA!", "category": "URGENTE"},
        {"hook": "OLHA O QUE ACONTECEU!", "category": "URGENTE"}
    ]
    
    # Filtra fallbacks que já foram usados recentemente
    safe_fallbacks = [f for f in fallbacks if f["hook"] not in recent_hooks]
    if not safe_fallbacks: safe_fallbacks = fallbacks
    
    choice = random.choice(safe_fallbacks)
    default_res = {
        "hook": choice["hook"], 
        "tag": "NOTÍCIA URGENTE", 
        "color": (255, 0, 0, 200), 
        "emoji": "1f6a8", 
        "hashtags": "#noticias #urgente",
        "category": choice["category"],
        "reactions": [("1f631", "Meu Deus!"), ("1f622", "Que triste"), ("1f621", "Absurdo!")]
    }
    
    if not GEMINI_KEY: return default_res
    
    # Lista de hooks para evitar no prompt
    evitar_str = ", ".join([f'"{h}"' for h in recent_hooks[:10]])
    
    CATEGORIES = {
        "URGENTE": {"tag": "NOTÍCIA URGENTE", "color": (255, 0, 0, 200)},
        "POLITICA": {"tag": "NA POLÍTICA", "color": (0, 102, 255, 200)},
        "ESPORTE": {"tag": "NO ESPORTE", "color": (50, 205, 50, 200)},
        "FOFOCA": {"tag": "VOCÊ NÃO VAI ACREDITAR", "color": (255, 215, 0, 200)},
        "CRIME": {"tag": "CRIME AGORA", "color": (0, 0, 0, 200)},
    }
    
    for attempt in range(3):
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}"
            prompt = (
                f"Analise a notícia: \"{title}\".\n"
                f"Atue como um editor de notícias sensacionalista de alto impacto.\n"
                f"Retorne APENAS uma linha no formato: HOOK | CATEGORY | EMOJI | HASHTAGS | REACTION_DATA\n"
                f"- HOOK: Título EXTREMAMENTE CURTO (MÁXIMO 3 PALAVRAS) em MAIÚSCULAS.\n"
                f"  REGRA DE CAMUFLAGEM: substitua letras por numeros/simbolos SOMENTE se o HOOK\n"
                f"  contiver EXATAMENTE uma destas palavras proibidas: MORTE, MORTO, MORREU, MATAR, MATOU, ASSASSINOU, ABUSO, DROGA.\n"
                f"- CATEGORY: URGENTE, POLITICA, ESPORTE, FOFOCA, CRIME.\n"
                f"- EMOJI: UM emoji para o tema.\n"
                f"- HASHTAGS: 3 a 5 hashtags.\n"
                f"- REACTION_DATA: 3 reações curtas no formato E1:TEXTO1,E2:TEXTO2,E3:TEXTO3\n"
                f"NÃO USE nenhum destes títulos (já usados recentemente): {evitar_str}.\n"
                f"SEJA CRIATIVO E VARIE O TOM!"
            )
            payload = {"contents":[{"parts":[{"text":prompt}]}]}
            r = requests.post(url, json=payload, timeout=60)
            r.raise_for_status()
            raw = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            if "|" in raw:
                parts = [p.strip() for p in raw.split("|")]
                if len(parts) >= 5:
                    hook = parts[0].replace('"', '').upper()
                    cat_key = parts[1].upper()
                    emoji_char = parts[2]
                    hashtags = parts[3].lower()
                    react_raw = parts[4]
                    
                    if hook not in recent_hooks:
                        reactions = []
                        for r_item in react_raw.split(","):
                            if ":" in r_item:
                                e_char, r_text = r_item.split(":", 1)
                                e_hex = emoji_to_hex(e_char.strip())
                                if e_hex: reactions.append((e_hex, r_text.strip()))
                        
                        config = CATEGORIES.get(cat_key, CATEGORIES["URGENTE"])
                        emoji_hex = emoji_to_hex(emoji_char) or "1f525"
                        return {
                            "hook": hook, "tag": config["tag"], "color": config["color"], 
                            "emoji": emoji_hex, "hashtags": hashtags, "category": cat_key,
                            "reactions": reactions[:3]
                        }
        except Exception as e:
            log.warning(f"Erro Gemini (tentativa {attempt}): {e}")
            

    return default_res


def gerar_titulo_misterioso(title):
    """Gera uma frase de mistério/curiosidade curta SEM revelar o desfecho da notícia."""
    if not GEMINI_KEY:
        return "VEJA O QUE ACONTECEU AGORA"
    
    for attempt in range(3):
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}"
            prompt = (
                f"Notícia: \"{title}\"\n"
                f"Crie uma única frase curta de mistério e choque para legenda de Facebook.\n"
                f"REGRAS OBRIGATÓRIAS:\n"
                f"1. NÃO revele o resultado, desfecho ou a notícia em si.\n"
                f"2. Crie CURIOSIDADE EXTREMA para o leitor clicar no link.\n"
                f"3. Use MAIÚSCULAS para dar ênfase.\n"
                f"4. Máximo 10 palavras.\n"
                f"5. Exemplo de tom: 'VEJA O QUE LULA DISSE SOBRE OS INTEGRANTES' ou 'VOCÊ NÃO VAI ACREDITAR NO QUE FOI REVELADO'.\n"
                f"Retorne APENAS a frase, sem explicações, emojis ou aspas."
            )
            payload = {"contents":[{"parts":[{"text":prompt}]}]}
            r = requests.post(url, json=payload, timeout=60)
            r.raise_for_status()
            frase = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            if frase:
                return frase.replace('"', '').upper()
        except Exception as e:
            log.warning(f"Erro ao gerar título misterioso (tentativa {attempt}): {e}")
    
    return "O QUE ACONTECEU VAI TE DEIXAR DE QUEIXO CAÍDO"


def adicionar_texto_premium(img_bytes, dados_esteticos):
    # dados_esteticos = {"hook", "tag", "color", "emoji", "reactions", "category"}
    MAIN_COLOR = dados_esteticos["color"]
    texto = dados_esteticos["hook"]
    tag_texto = dados_esteticos["tag"]
    emoji_hex = dados_esteticos["emoji"]
    reactions = dados_esteticos.get("reactions", [])

    img = Image.open(BytesIO(img_bytes)).convert("RGB")
    w, h = img.size

    # --- CONFIGURAÇÃO SUPERSAMPLING (2x para 1080x1080 interno) ---
    sf = 2
    base_side = 1080
    bw = bh = base_side * sf

    # 1. Crop quadrado da imagem original
    side = min(w, h)
    left = (w - side) / 2
    top = (h - side) / 2
    img_sq = img.crop((left, top, left + side, top + side))
    
    # 2. Redimensionamento e Melhoria da imagem base (1:1)
    img_core = img_sq.resize((bw, bh), Image.Resampling.LANCZOS)
    img_core = ImageEnhance.Color(img_core).enhance(1.3)
    img_core = ImageEnhance.Contrast(img_core).enhance(1.1)
    img_core = ImageEnhance.Sharpness(img_core).enhance(1.4)

    # 3. Gradiente de base (escurecer parte inferior para leitura do título)
    overlay = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    grad_h = int(bh * 0.50)
    for y in range(bh - grad_h, bh):
        alpha = int(240 * ((y - (bh - grad_h)) / grad_h))
        draw_ov.line([(0, y), (bw, y)], fill=(0, 0, 0, max(0, min(255, alpha))))
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=5 * sf))
    img_core = Image.alpha_composite(img_core.convert("RGBA"), overlay)
    
    draw_core = ImageDraw.Draw(img_core)
    font_path = baixar_fonte()

    # 4. Selo de Categoria (Topo)
    badge_h = int(bh * 0.05)
    f_badge = ImageFont.truetype(font_path, int(badge_h * 0.75)) if font_path else ImageFont.load_default()
    bbox_b = draw_core.textbbox((0, 0), tag_texto, font=f_badge)
    badge_w = (bbox_b[2] - bbox_b[0]) + (40 * sf)
    bx1, by1 = 30 * sf, 40 * sf
    bx2, by2 = bx1 + badge_w, by1 + badge_h
    draw_core.rectangle([bx1, by1, bx2, by2], fill=MAIN_COLOR)
    draw_core.text(((bx1 + bx2) // 2, (by1 + by2) // 2), tag_texto, font=f_badge, fill=(255, 255, 255), anchor="mm")

    # 5. Título (HOOK) — posicionado na parte inferior do 1:1
    texto_puro = limpar_emojis(texto)
    f_size = int(bh * 0.10)
    font = ImageFont.truetype(font_path, f_size) if font_path else ImageFont.load_default()

    l = texto_puro.strip()
    bb = draw_core.textbbox((0, 0), l, font=font)
    lw, lh = bb[2] - bb[0], bb[3] - bb[1]

    if lw > (bw - 100 * sf):
        f_size = int(f_size * (bw - 100 * sf) / lw)
        font = ImageFont.truetype(font_path, f_size) if font_path else ImageFont.load_default()
        bb = draw_core.textbbox((0, 0), l, font=font)
        lw, lh = bb[2] - bb[0], bb[3] - bb[1]

    tx = (bw - lw) // 2
    padding = 35 * sf
    ty = int(bh * 0.85) - lh # Posicionado no terço inferior do quadrado

    # Fundo do Título (Box)
    tx1, ty1 = tx - padding, ty - padding
    tx2, ty2 = tx + lw + padding, ty + lh + padding
    temp_box = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    ImageDraw.Draw(temp_box).rectangle([tx1, ty1, tx2, ty2], fill=MAIN_COLOR)
    img_core = Image.alpha_composite(img_core, temp_box)

    # SOMBRA DO TÍTULO
    cx, cy = (tx1 + tx2) // 2, (ty1 + ty2) // 2
    shadow_layer = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_layer)
    s_draw.text((cx + 4 * sf, cy + 4 * sf), l, font=font, fill=(0, 0, 0, 200), anchor="mm")
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=3 * sf))
    img_core = Image.alpha_composite(img_core, shadow_layer)

    # Texto do Título
    draw_core = ImageDraw.Draw(img_core)
    draw_core.text((cx, cy), l, font=font, fill=(255, 255, 255), anchor="mm")

    # 6. Ícone Principal (acima do título)
    try:
        emoji_url = f"https://raw.githubusercontent.com/iamcal/emoji-data/master/img-apple-160/{emoji_hex}.png"
        r_emoji = requests.get(emoji_url, timeout=10)
        if r_emoji.status_code == 200:
            e_img = Image.open(BytesIO(r_emoji.content)).convert("RGBA")
            e_size = int(f_size * 1.5)
            e_img = e_img.resize((e_size, e_size), Image.Resampling.LANCZOS)
            ix, iy = (bw - e_size) // 2, ty1 - e_size - (2 * sf)
            
            # Sombra do Ícone Principal
            e_shadow = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
            ImageDraw.Draw(e_shadow).ellipse(
                [ix + 6*sf, iy + 6*sf, ix + e_size + 6*sf, iy + e_size + 6*sf],
                fill=(0, 0, 0, 150)
            )
            e_shadow = e_shadow.filter(ImageFilter.GaussianBlur(radius=6*sf))
            img_core = Image.alpha_composite(img_core, e_shadow)
            
            img_core.paste(e_img, (ix, iy), e_img)
    except: pass

    # 7. Emojis de Reação (Opinião ao lado direito)
    if reactions:
        # Posição: um pouco abaixo do título, dentro do quadrado 1:1
        render_y = ty2 + int(60 * sf)
        r_emoji_size = int(bh * 0.05) 
        f_react_size = int(bh * 0.025)
        f_react = ImageFont.truetype(font_path, f_react_size) if font_path else ImageFont.load_default()

        # Calcular largura total
        gap = int(40 * sf)
        sp = int(10 * sf)
        items = []
        tot_w = 0
        
        for (r_hex, r_text) in reactions:
            lbb = draw_core.textbbox((0, 0), r_text, font=f_react)
            lw_r = lbb[2] - lbb[0]
            item_w = r_emoji_size + sp + lw_r
            items.append({"hex": r_hex, "text": r_text, "w": item_w})
            tot_w += item_w
        
        tot_w += gap * (len(reactions) - 1)
        rx = (bw - tot_w) // 2

        for item in items:
            try:
                # Tentar Facebook style primeiro, fallback para Apple
                r_url = f"https://raw.githubusercontent.com/iamcal/emoji-data/master/img-facebook-96/{item['hex']}.png"
                r_res = requests.get(r_url, timeout=5)
                if r_res.status_code != 200:
                    r_url = f"https://raw.githubusercontent.com/iamcal/emoji-data/master/img-apple-160/{item['hex']}.png"
                    r_res = requests.get(r_url, timeout=5)
                
                if r_res.status_code == 200:
                    ri = Image.open(BytesIO(r_res.content)).convert("RGBA")
                    ri = ri.resize((r_emoji_size, r_emoji_size), Image.Resampling.LANCZOS)
                    img_core.paste(ri, (rx, render_y), ri)
                    
                    tx_p = rx + r_emoji_size + sp
                    ty_p = render_y + (r_emoji_size // 2)
                    
                    draw_core.text((tx_p + 1*sf, ty_p + 1*sf), item["text"], font=f_react, fill=(0, 0, 0, 180), anchor="lm")
                    draw_core.text((tx_p, ty_p), item["text"], font=f_react, fill=(255, 255, 255), anchor="lm")
                    
                    rx += item["w"] + gap
            except Exception as e:
                log.warning(f"Erro ao renderizar reação {item['hex']}: {e}")

    # --- FINALIZAÇÃO: REDUÇÃO PARA 1080x1080 PADRÃO ---
    final_img = img_core.resize((base_side, base_side), Image.Resampling.LANCZOS).convert("RGB")
    out = BytesIO()
    final_img.save(out, format="JPEG", quality=98)
    return out.getvalue()


def get_noticias():
    from playwright.sync_api import sync_playwright
    res = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            log.info("Acessando SFY...")
            page.goto(SFY_LOGIN)
            page.fill("input[name='email']", SFY_EMAIL)
            page.fill("input[name='password']", SFY_PASSWORD)
            page.click("button[type='submit']")
            page.wait_for_url("**/dashboard**", timeout=40000)
            page.goto(SFY_SHARE)
            page.wait_for_timeout(7000)
            
            log.info("Selecionando bloco Sharesforyou...")
            try:
                page.click("button.change-order-by:has-text('Sharesforyou')", timeout=15000)
                page.wait_for_timeout(10000)
            except Exception as e:
                log.warning(f"Não foi possível clicar no botão Sharesforyou (pode já estar selecionado): {e}")

            cards = page.locator(".card").all()
            log.info(f"Encontrados {len(cards)} cards no bloco Sharesforyou.")
            
            for card in cards:
                try:
                    title = card.locator("h5, p.fs-4").first.inner_text().strip()
                    link = card.locator("a:has(i.ti-eye)").first.get_attribute("href")
                    img = card.locator("img").first.get_attribute("src")
                    if link and title:
                        if link.startswith("/"): link = "https://www.sharesforyou.com" + link
                        if img and img.startswith("/"): img = "https://www.sharesforyou.com" + img
                        
                        res.append({"id": make_article_id(link, title), "title": title, "link": link, "img": img})
                except: continue
        except Exception as e: log.error(f"Erro Playwright: {e}")
        finally: browser.close()
    return res

def main():
    log.info("Bot Profissional Notícias Iniciado.")
    
    # Ler tokens diretamente das variáveis de ambiente (padrão do GitHub Actions)
    load_dotenv(override=True)
    FB_PAGE_ID = os.environ.get("FB_PAGE_ID", "").strip()
    FB_TOKEN   = os.environ.get("FB_TOKEN", "").strip()
    
    if not FB_TOKEN or not FB_PAGE_ID:
        log.error("❌ FB_TOKEN ou FB_PAGE_ID não configurados. Encerrando.")
        return
    
    log.info(f"🔑 PAGE_ID: {FB_PAGE_ID}")
    log.info(f"🔑 TOKEN: {FB_TOKEN[:20]}...")

    posted = load_posted()
    news = get_noticias()
    if not news:
        log.warning("Nenhuma notícia encontrada.")
        return
    
    # Filtra apenas o que não foi postado
    new_news = [n for n in news if n["id"] not in posted]
    
    if not new_news:
        log.info("📢 Nenhuma notícia nova para postar. Encerrando para evitar repetição.")
        return
    
    log.info(f"🆕 Encontradas {len(new_news)} notícias inéditas. Tentando postar a primeira...")

    for n in new_news:
        try:
            # Baixar imagem apenas agora (economiza banda e tempo)
            if not n.get("img"):
                log.warning(f"⚠️ Sem imagem para: {n['title'][:50]}")
                continue
                
            log.info(f"📥 Baixando imagem: {n['img'][:60]}...")
            r_img = requests.get(n["img"], headers={"User-Agent": HEADERS["User-Agent"]}, timeout=20)
            if r_img.status_code != 200:
                log.warning(f"⚠️ Imagem retornou {r_img.status_code}, pulando.")
                continue
            img_data = r_img.content
            
            estetica = gerar_gancho(n["title"])
            
            # Trava Adicional: Título Visual (Histórico Recente)
            recent_hooks = load_recent_hooks()
            if estetica["hook"] in recent_hooks:
                log.warning(f"🚫 Hook '{estetica['hook']}' já usado recentemente. Pulando para garantir variedade.")
                continue

            img_b = adicionar_texto_premium(img_data, estetica)
            
            misterio = gerar_titulo_misterioso(n["title"])
            hashtags = estetica.get("hashtags", "#noticias #brasil").lower()
            padding_bottom = "\n.\n.\n.\n.\n.\n"
            
            # Formato: 😱 TAG: MISTERIO... 😱
            msg = f"😱 {estetica['tag'].upper()}: {misterio}... 😱\n.\n{hashtags}{padding_bottom}🔗 VEJA MAIS NO LINK: {n['link']}"

            log.info("📤 Enviando para o Facebook...")
            r_fb = requests.post(
                f"{FB_GRAPH}/{FB_PAGE_ID}/photos",
                files={"source": ("f.jpg", img_b, "image/jpeg")},
                data={"message": msg, "access_token": FB_TOKEN, "published": "true"},
                timeout=60
            )
            resp_data = r_fb.json()
            if "id" in resp_data:
                post_id = resp_data["id"]
                log.info(f"✅ PUBLICADO! ID: {post_id}")
                log.info(f"🔗 LINK: https://www.facebook.com/{FB_PAGE_ID}/posts/{post_id.split('_')[-1]}")
                posted.add(n["id"])
                save_posted(posted)
                save_new_hook(estetica["hook"])
                break
            else:
                log.error(f"Erro FB: {resp_data}")
        except Exception as e: 
            log.error(f"Erro no loop principal: {e}")
            log.error(traceback.format_exc())

if __name__ == "__main__": main()
