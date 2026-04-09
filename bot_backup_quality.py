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
FB_PAGE_ID   = os.environ.get("FB_PAGE_ID", "")
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

def make_article_id(url):
    return hashlib.sha256(url.encode()).hexdigest()[:16]

def baixar_fonte(emoji=False):
    if emoji:
        for f in ["C:\\Windows\\Fonts\\seguiemj.ttf"]:
            if os.path.exists(f): return f
    # Priorizar Impact para alto impacto, Arial Black como segunda opção
    for f in ["C:\\Windows\\Fonts\\impact.ttf", "C:\\Windows\\Fonts\\ariblk.ttf", "fonts/NotoSans-Bold.ttf", "C:\\Windows\\Fonts\\arialbd.ttf"]:
        if os.path.exists(f): return f
    return None

def limpar_emojis(texto):
    # Preserva caracteres acentuados e pontuação, removendo apenas o que não é texto 'humano'
    return re.sub(r'[^\w\s.,!?;:\"\'\(\)\-\u00C0-\u00FF]+', '', texto).strip()

def gerar_gancho(title):
    if not GEMINI_KEY: return "VOCÊ NÃO VAI ACREDITAR! 😱"
    try:
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        prompt = (
            f"Como um mestre de clickbait sensacionalista brasileiro, crie um título CURTO e IMPACTANTE (máximo 5 palavras). "
            f"Use UM emoji impactante no final (ex: 💀, 😱, 🔥). Ex: NINGUÉM ACREDITOU NISSO! 😱. "
            f"Evite frases genéricas sem sentido. Notícia: \"{title}\". Título em MAIÚSCULAS."
        )
        payload = {"contents":[{"parts":[{"text":prompt}]}]}
        r = requests.post(url, json=payload, timeout=15)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip().upper().replace('"', '')
    except Exception as e:
        log.warning(f"Erro Gemini: {e}")
        return "OUÇA ESTA REVELAÇÃO! 😱"

def adicionar_texto_premium(img_bytes, texto):
    # Paleta de Cores Noticiário (Transparência de 170 conforme solicitado)
    PALETTES = [
        (220, 20, 60, 170),   # Vermelho Alerta
        (0, 51, 153, 170),    # Azul Marinho News
        (15, 15, 15, 170),    # Preto Profundo
    ]
    MAIN_COLOR = random.choice(PALETTES)

    img = Image.open(BytesIO(img_bytes)).convert("RGB")
    w, h = img.size

    # Zoom/Crop
    zoom = 1.15
    nw, nh = int(w * zoom), int(h * zoom)
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left, top = int((nw - w) / 2), int((nh - h) / 2)
    img = img.crop((left, top, left + w, top + h))
    img = ImageEnhance.Color(img).enhance(1.3)
    img = ImageEnhance.Contrast(img).enhance(1.1)
    img = ImageEnhance.Sharpness(img).enhance(1.4) # Adiciona nitidez profissional

    # 1. Gradiente de Base Ampliado (Subindo)
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    grad_h = int(h * 0.70)
    for y in range(h - grad_h, h):
        alpha = int(245 * ((y - (h - grad_h)) / grad_h))
        draw_ov.line([(0, y), (w, y)], fill=(0, 0, 0, max(0, min(255, alpha))))
    
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=5))
    if img.size != overlay.size:
        overlay = overlay.resize(img.size)
    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(img)
    font_path = baixar_fonte()
    emoji_font_path = baixar_fonte(emoji=True)

    # 2. Selo URGENTE (Correção de Largura)
    badge_h = int(h * 0.05)
    f_badge = ImageFont.truetype(font_path, int(badge_h * 0.7)) if font_path else ImageFont.load_default()
    txt_badge = "NOTÍCIA URGENTE"
    bbox_b = draw.textbbox((0,0), txt_badge, font=f_badge)
    badge_w = (bbox_b[2] - bbox_b[0]) + 40
    draw.rectangle([20, 30, 20 + badge_w, 30 + badge_h], fill=(220, 20, 60, 255))
    draw.text((40, 30 + (badge_h - int(badge_h * 0.7))//2 - 2), txt_badge, font=f_badge, fill=(255, 255, 255))

    texto_puro = limpar_emojis(texto)
    has_emoji = any(ord(c) > 127 for c in texto)
    
    # 3. Caixa de Texto CENTRALIZADA e RESPONSIVA
    f_size = int(h * 0.09) 
    font = ImageFont.truetype(font_path, f_size) if font_path else ImageFont.load_default()
    # Aumentar largura para 25 conforme solicitado
    lines = textwrap.wrap(texto_puro, width=25)
    
    line_metrics = []
    max_lw = 0
    total_lh = 0
    for l in lines:
        bb = draw.textbbox((0, 0), l, font=font)
        lw, lh = bb[2] - bb[0], bb[3] - bb[1]
        line_metrics.append((l, lw, lh))
        max_lw = max(max_lw, lw)
        total_lh += lh + 15

    tx = (w - max_lw) // 2
    padding = 30
    # Posicionamento Dinâmico (Proporcional ao h) - CENTRO INFERIOR (Ajustado para respiro)
    ty = int(h * 0.75) - (total_lh // 2)
    
    # Fundo UNIFICADO Noticiário
    temp_box = Image.new("RGBA", (w, h), (0,0,0,0))
    draw_box = ImageDraw.Draw(temp_box)
    draw_box.rectangle([tx-padding, ty-padding, tx+max_lw+padding, ty+total_lh-15+padding], fill=MAIN_COLOR)
    img = Image.alpha_composite(img, temp_box)
    
    # Desenhar Título EM NEGRITO e com REALCE EXTRA
    draw = ImageDraw.Draw(img)
    curr_y = ty
    for l, lw, lh in line_metrics:
        lx = tx + (max_lw - lw) // 2
        # Sombra Leve (Preto com leve offset e opacidade baixa)
        draw.text((lx+4, curr_y+4), l, font=font, fill=(0,0,0,160), align="center")
        # Texto Principal (Branco) - REMOVIDO STROKE conforme solicitado
        draw.text((lx, curr_y), l, font=font, fill=(255, 255, 255), align="center")
        curr_y += lh + 15
        
    # 4. Ícone PREMIUM (Estilo iPhone) CENTRALIZADO
    EMOJI_MAP = {
        "🚨": "1f6a8", "💀": "1f480", "🔥": "1f525", "💣": "1f4a3", "⚠️": "26a0"
    }
    icons = ["🚨", "💀", "🔥", "💣", "⚠️"]
    char = random.choice(icons)
    hex_code = EMOJI_MAP.get(char, "1f480")
    emoji_url = f"https://raw.githubusercontent.com/iamcal/emoji-data/master/img-apple-160/{hex_code}.png"
    
    try:
        r_emoji = requests.get(emoji_url, timeout=10)
        if r_emoji.status_code == 200:
            emoji_img = Image.open(BytesIO(r_emoji.content)).convert("RGBA")
            # Redimensionar ícone proporcionalmente (ligeiramente menor agora: 1.6)
            e_size = int(f_size * 1.6)
            emoji_img = emoji_img.resize((e_size, e_size), Image.Resampling.LANCZOS)
            
            # Centralização perfeita
            ix = (w - e_size) // 2
            iy = ty - e_size - 10 # Logo acima do bloco de texto com respiro
            
            # Sombra do Ícone para profundidade
            shadow = Image.new("RGBA", (e_size, e_size), (0,0,0,0))
            ImageDraw.Draw(shadow).ellipse([5, 5, e_size-5, e_size-5], fill=(0,0,0,150))
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=10))
            img.paste(shadow, (ix+8, iy+8), shadow)
            
            # Colar o emoji
            img.paste(emoji_img, (ix, iy), emoji_img)
    except Exception as e:
        log.warning(f"Erro ao carregar emoji premium: {e}")

    # 5. CTA DINÂMICO (Posicionado sob o título)
    f_sub_size = int(badge_h * 0.8)
    f_sub = ImageFont.truetype(font_path, f_sub_size) if font_path else ImageFont.load_default()
    cta_t = 'Clique em "...mais" para ver na íntegra'
    bw_cta = draw.textbbox((0,0), cta_t, font=f_sub)
    cx = (w - (bw_cta[2]-bw_cta[0]))//2
    # Posição fixa no EXTREMO INFERIOR
    cy = h - 45 
    
    # Sombra CTA
    draw.text((cx+3, cy+3), cta_t, font=f_sub, fill=(0,0,0,220))
    draw.text((cx, cy), cta_t, font=f_sub, fill=(255, 215, 0))

    out = BytesIO(); img.convert("RGB").save(out, format="JPEG", quality=98)
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
            for card in page.locator(".card").all():
                try:
                    title = card.locator("h5, p.fs-4").first.inner_text().strip()
                    link = card.locator("a:has(i.ti-eye)").first.get_attribute("href")
                    img = card.locator("img").first.get_attribute("src")
                    if link and title:
                        if link.startswith("/"): link = "https://www.sharesforyou.com" + link
                        if img and img.startswith("/"): img = "https://www.sharesforyou.com" + img
                        res.append({"id":make_article_id(link), "title":title, "link":link, "img":img})
                except: continue
        except Exception as e: log.error(f"Erro Playwright: {e}")
        finally: browser.close()
    return res

def main():
    log.info("Bot Profissional Notícias Iniciado.")
    
    # 0. Tentativa de Renovação Automática do Token
    try:
        from auth_manager import auto_renew_meta_token
        auto_renew_meta_token()
        # Recarrega variáveis após possível renovação
        load_dotenv(override=True)
        global FB_TOKEN
        FB_TOKEN = os.environ.get("FB_TOKEN", FB_TOKEN)
    except Exception as e:
        log.warning(f"Aviso: Não foi possível processar renovação automática: {e}")

    posted = load_posted()
    session = make_session()
    news = get_noticias()
    if not news: return
    
    for n in news:
        if n["id"] in posted: continue
        try:
            if not n["img"]: continue
            r = session.get(n["img"], timeout=15)
            if r.status_code != 200: continue
            
            hook = gerar_gancho(n["title"])
            img_b = adicionar_texto_premium(r.content, hook)
            
            padding = "\n.\n.\n.\n.\n.\n"
            msg = f"😱 {n['title'].upper()} 😱\n\nNotícia urgente! Veja os detalhes chocantes agora... 💣🔥\n{padding}🔗 LINK: {n['link']}"
            
            r_fb = requests.post(
                f"{FB_GRAPH}/{FB_PAGE_ID}/photos",
                files={"source": ("f.jpg", img_b, "image/jpeg")},
                data={"message": msg, "access_token": FB_TOKEN, "published": "true"},
                timeout=60
            )
            if "id" in r_fb.json():
                post_id = r_fb.json()["id"]
                log.info(f"✓ PUBLICADO! ID: {post_id}")
                log.info(f"LINK: https://www.facebook.com/{FB_PAGE_ID}/posts/{post_id.split('_')[-1]}")
                posted.add(n["id"]); save_posted(posted)
                break
            else:
                log.error(f"Erro FB: {r_fb.json()}")
        except Exception as e: 
            log.error(f"Erro no loop principal: {e}")
            log.error(traceback.format_exc())

if __name__ == "__main__": main()
