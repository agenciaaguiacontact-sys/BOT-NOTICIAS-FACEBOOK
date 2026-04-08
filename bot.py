#!/usr/bin/env python3
"""
SharesForYou → Facebook Auto-Poster Bot
Versão FINAL - Estável e Validada
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

MAX_IMG_BYTES = 3_500_000

def make_session():
    s = requests.Session()
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
        payload = {"contents":[{"parts":[{"text":f"Escreva uma frase curta e bombástica de até 8 palavras para esta notícia: \"{title}\". Apenas a frase em MAIÚSCULAS."}]}]}
        r = requests.post(url, json=payload, timeout=15)
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip().upper()
    except: return "CLICK PARA VER!"

def baixar_fonte():
    for f in ["fonts/NotoSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:\\Windows\\Fonts\\arialbd.ttf"]:
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
    tx, ty = (w-(bbox[2]-bbox[0]))//2, fy+(fh-(bbox[3]-bbox[1]))//2
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
            # Seletores específicos para evitar inputs ocultos
            page.wait_for_selector("input[type='email']", timeout=20000)
            page.fill("input[type='email']", SFY_EMAIL)
            page.fill("input[type='password']", SFY_PASSWORD)
            page.click("button.btn-primary, button[type='submit']")
            
            page.wait_for_url("**/dashboard**", timeout=40000)
            log.info("Login OK. Navegando para notícias...")
            page.goto(SFY_SHARE)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(5000)
            
            # Extração
            cards = page.locator(".card").all()
            log.info(f"Encontrados {len(cards)} cards.")
            
            for card in cards:
                try:
                    title = card.locator("h5, p.fs-4").first.inner_text().strip()
                    # Link (Olho)
                    eye = card.locator("a:has(i.ti-eye)").first
                    link = eye.get_attribute("href")
                    # Imagem
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
    log.info("Iniciando Bot...")
    if not all([SFY_EMAIL, SFY_PASSWORD, FB_PAGE_ID, FB_TOKEN]):
        log.error("Credenciais faltando."); return

    posted = load_posted()
    news = get_noticias_playwright()
    if not news: log.warning("Nenhuma notícia encontrada."); return
    
    for n in news:
        if n["id"] in posted: continue
        log.info(f"Postando » {n['title']}")
        try:
            r = requests.get(n["img"], timeout=15) if n["img"] else None
            img_b = r.content if r and r.status_code == 200 else None
            if not img_b: continue
            
            final_img = adicionar_texto(img_b, gerar_gancho(n["title"]), int(n["id"][:2], 16))
            
            # Facebook Upload
            r_up = requests.post(f"{FB_GRAPH}/{FB_PAGE_ID}/photos", files={"source":("f.jpg", final_img)}, data={"access_token":FB_TOKEN,"published":"false"})
            photo_id = r_up.json().get("id")
            if not photo_id: continue
            
            # Facebook Post
            r_pt = requests.post(f"{FB_GRAPH}/{FB_PAGE_ID}/feed", data={"message":f"🔥 {n['title']}\n\n👇 VEJA NO COMENTÁRIO!", "attached_media[0]":json.dumps({"media_fbid":photo_id}), "access_token":FB_TOKEN})
            post_id = r_pt.json().get("id")
            if not post_id: continue
            
            time.sleep(2)
            requests.post(f"{FB_GRAPH}/{post_id}/comments", data={"message":f"🔗 Leia a matéria completa: {n['link']}", "access_token":FB_TOKEN})
            
            posted.add(n["id"]); save_posted(posted)
            log.info("✓ SUCESSO!"); break
        except Exception as e: log.error(f"Erro loop: {e}"); continue

if __name__ == "__main__": main()
