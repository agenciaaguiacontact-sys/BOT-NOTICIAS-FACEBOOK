#!/usr/bin/env python3
"""
SharesForYou → Facebook Auto-Poster Bot
Versão FINAL - Headers Corrigidos
"""

import os
import json
import time
import logging
import hashlib
import textwrap
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

load_dotenv()

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
FB_GRAPH     = "https://graph.facebook.com/v25.0"

# Headers para evitar 403
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
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

def gerar_gancho(title):
    if not GEMINI_KEY: return "NOTÍCIA DO DIA!"
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        payload = {"contents":[{"parts":[{"text":f"Escreva uma frase bombástica de de até 8 palavras para esta notícia: \"{title}\". Apenas a frase em MAIÚSCULAS."}]}]}
        r = requests.post(url, json=payload, timeout=15)
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip().upper()
    except: return "CLICK PARA VER!"

def baixar_fonte():
    for f in ["fonts/NotoSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", "C:\\Windows\\Fonts\\arialbd.ttf"]:
        if os.path.exists(f): return f
    return None

def adicionar_texto(img_bytes, texto, p_idx):
    palettes = [{"bg":(220,20,60),"tx":(255,255,255)}, {"bg":(0,100,200),"tx":(255,255,255)}, {"bg":(30,30,30),"tx":(255,215,0)}]
    p = palettes[p_idx % len(palettes)]
    img = Image.open(BytesIO(img_bytes)).convert("RGB")
    w, h = img.size
    fh = int(h*0.35); fy = h-fh
    overlay = Image.new("RGBA", (w,h), (0,0,0,0))
    ImageDraw.Draw(overlay).rectangle([0,fy,w,h], fill=(*p["bg"], 220))
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"), (0,0))
    font_path, txt = baixar_fonte(), textwrap.fill(texto, width=18)
    font = ImageFont.truetype(font_path, 60) if font_path else ImageFont.load_default()
    draw = ImageDraw.Draw(img)
    bbox = draw.multiline_textbbox((0,0), txt, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    tx, ty = (w-tw)//2, fy+(fh-th)//2
    draw.multiline_text((tx,ty), txt, font=font, fill=p["tx"], align="center", spacing=10)
    out = BytesIO(); img.save(out, format="JPEG", quality=85)
    return out.getvalue()

def get_noticias_playwright():
    from playwright.sync_api import sync_playwright
    res = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width":1280,"height":800})
        try:
            log.info("Acessando login...")
            page.goto(SFY_LOGIN)
            page.wait_for_selector("input[type='email']", timeout=20000)
            page.fill("input[type='email']", SFY_EMAIL)
            page.fill("input[type='password']", SFY_PASSWORD)
            page.click("button.btn-primary")
            page.wait_for_url("**/dashboard**", timeout=40000)
            log.info("Navegando para notícias...")
            page.goto(SFY_SHARE)
            page.wait_for_timeout(7000)
            
            cards = page.locator(".card").all()
            for card in cards:
                try:
                    title = card.locator("h5, p.fs-4").first.inner_text().strip()
                    eye = card.locator("a:has(i.ti-eye)").first
                    link = eye.get_attribute("href")
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
    log.info("Bot Iniciado.")
    posted = load_posted()
    session = make_session()
    news = get_noticias_playwright()
    if not news: log.warning("Fim: Nenhuma notícia."); return
    
    for n in news:
        if n["id"] in posted: continue
        log.info(f"Processando: {n['title']}")
        try:
            if not n["img"]: continue
            r = session.get(n["img"], timeout=15)
            if r.status_code != 200:
                log.warning(f"Passe: Erro imagem {r.status_code}")
                continue
            
            hook = gerar_gancho(n["title"])
            img_b = adicionar_texto(r.content, hook, int(n["id"][:2], 16))
            
            # Post
            r_fb = requests.post(
                f"{FB_GRAPH}/{FB_PAGE_ID}/photos",
                files={"source": ("f.jpg", img_b, "image/jpeg")},
                data={"message": f"🔥 {n['title']}\n\n👇 VEJA A MATÉRIA COMPLETA NO PRIMEIRO COMENTÁRIO!", "access_token": FB_TOKEN, "published": "true"},
                timeout=60
            )
            resp = r_fb.json()
            if "id" in resp:
                post_id = resp.get("post_id") or resp.get("id")
                log.info(f"✓ PUBLICADO! ID: {post_id}")
                time.sleep(3)
                r_link = requests.get(f"{FB_GRAPH}/{post_id}?fields=permalink_url&access_token={FB_TOKEN}")
                log.info(f"LINK: {r_link.json().get('permalink_url')}")
                requests.post(f"{FB_GRAPH}/{post_id}/comments", data={"message":f"🔗 Notícia aqui: {n['link']}", "access_token":FB_TOKEN})
                posted.add(n["id"]); save_posted(posted)
                break
            else: log.error(f"Falha FB: {resp}")
        except Exception as e: log.error(f"Erro: {e}")

if __name__ == "__main__": main()
