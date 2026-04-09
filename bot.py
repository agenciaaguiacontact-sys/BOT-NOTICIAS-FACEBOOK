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

def make_article_id(url):
    # Remove query strings para evitar duplicatas por parâmetros de rastreio
    clean_url = url.split("?")[0].split("#")[0]
    return hashlib.sha256(clean_url.encode()).hexdigest()[:16]

def load_last_title():
    if os.path.exists("last_title.txt"):
        try: return open("last_title.txt", "r", encoding="utf-8").read().strip()
        except: return ""
    return ""

def save_last_title(title):
    try: open("last_title.txt", "w", encoding="utf-8").write(title)
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

def gerar_gancho(title):
    default_res = {"hook": "REVELAÇÃO CHOCANTE!", "tag": "NOTÍCIA URGENTE", "color": (255, 0, 0, 200), "emoji": "1f6a8"}
    if not GEMINI_KEY: return default_res
    
    last_t = load_last_title()
    
    # Mapeamento de Categorias, Cores e Tags
    CATEGORIES = {
        "URGENTE": {"tag": "NOTÍCIA URGENTE", "color": (255, 0, 0, 200)},
        "POLITICA": {"tag": "NA POLÍTICA", "color": (0, 102, 255, 200)},
        "ESPORTE": {"tag": "NO ESPORTE", "color": (50, 205, 50, 200)},
        "FOFOCA": {"tag": "VOCÊ NÃO VAI ACREDITAR", "color": (255, 215, 0, 200)},
        "CRIME": {"tag": "CRIME AGORA", "color": (0, 0, 0, 200)},
    }
    
    EMOJI_HEX = {
        "🚨": "1f6a8", "💀": "1f480", "🔥": "1f525", "💣": "1f4a3", "⚠️": "26a0", 
        "😱": "1f631", "👀": "1f440", "📢": "1f4e2", "💰": "1f4b0", "🚔": "1f694",
        "⚽": "26bd", "🎭": "1f3ad", "🤐": "1f910"
    }

    for attempt in range(3):
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}"
            prompt = (
                f"Analise a notícia: \"{title}\".\n"
                f"Atue como um editor de notícias sensacionalista de alto impacto.\n"
                f"Retorne APENAS uma linha no formato: HOOK | CATEGORY | EMOJI\n"
                f"- HOOK: Título EXTREMAMENTE CURTO (MÁXIMO 3 PALAVRAS) em MAIÚSCULAS.\n"
                f"  REGRA DE CAMUFLAGEM: substitua letras por numeros/simbolos SOMENTE se o HOOK\n"
                f"  contiver EXATAMENTE uma destas palavras proibidas:\n"
                f"  MORTE, MORTO, MORREU, MATAR, MATOU, MATARAM, ASSASSINOU, ASSASSINATO,\n"
                f"  ESPANCOU, SANGUE, TIRO, TIROS, BALEADO, ESTUPRO, ESTUPROU, ABUSO,\n"
                f"  TRAFICO, DROGA, DROGAS, COCAINA, CRACK.\n"
                f"  Exemplos CORRETOS: MORTE->M0RT3, MATOU->M@T0U, TIRO->T1R0, SANGUE->S@NGU3, ESTUPRO->3STUPR0.\n"
                f"  PROIBIDO substituir letras em qualquer outra palavra. Exemplos INTACTOS:\n"
                f"  BALE, INSANO, INVASAO, COPA, TREINO, BRASIL, POLICIA, ACIDENTE, ESPORTE,\n"
                f"  VENCE, GANHA, REVELA, FLAGRA, CHOCA, SURPREENDE, BRIGA, CRISE, e qualquer outra.\n"
                f"- CATEGORY: Escolha exatamente uma: URGENTE, POLITICA, ESPORTE, FOFOCA, CRIME.\n"
                f"- EMOJI: UM único emoji que combine com o tema.\n"
                f"Não repita o último título: \"{last_t}\"."
            )
            payload = {"contents":[{"parts":[{"text":prompt}]}]}
            r = requests.post(url, json=payload, timeout=15)
            r.raise_for_status()
            raw = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            if "|" in raw:
                parts = [p.strip() for p in raw.split("|")]
                if len(parts) >= 3:
                    hook = parts[0].replace('"', '').upper()
                    cat_key = parts[1].upper()
                    emoji_char = parts[2]
                    
                    if hook != last_t:
                        save_last_title(hook)
                        config = CATEGORIES.get(cat_key, CATEGORIES["URGENTE"])
                        emoji_hex = EMOJI_HEX.get(emoji_char, "1f525") 
                        return {
                            "hook": hook, 
                            "tag": config["tag"],
                            "color": config["color"], 
                            "emoji": emoji_hex
                        }
        except Exception as e:
            log.warning(f"Erro Gemini (tentativa {attempt}): {e}")
            
    return default_res

def adicionar_texto_premium(img_bytes, dados_esteticos):
    # dados_esteticos = {"hook": "...", "tag": "...", "color": (R,G,B,A), "emoji": "hex_code"}
    MAIN_COLOR = dados_esteticos["color"]
    texto = dados_esteticos["hook"]
    tag_texto = dados_esteticos["tag"]
    emoji_hex = dados_esteticos["emoji"]

    img = Image.open(BytesIO(img_bytes)).convert("RGB")
    w, h = img.size
    
    # --- PADRONIZAÇÃO 1:1 (QUADRADA) ---
    side = min(w, h)
    left = (w - side) / 2
    top = (h - side) / 2
    img_sq = img.crop((left, top, left + side, top + side))
    
    # --- CONFIGURAÇÃO SUPERSAMPLING (2x para 1080x1080) ---
    sf = 2
    target_side = 1080
    bw = bh = target_side * sf

    # 1. Redimensionamento em Alta Definição
    img_hd = img_sq.resize((bw, bh), Image.Resampling.LANCZOS)
    img_hd = ImageEnhance.Color(img_hd).enhance(1.3)
    img_hd = ImageEnhance.Contrast(img_hd).enhance(1.1)
    img_hd = ImageEnhance.Sharpness(img_hd).enhance(1.4) 

    # 2. Gradiente de Base Ampliado (Mais denso no 1:1)
    overlay = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    grad_h = int(bh * 0.70)
    for y in range(bh - grad_h, bh):
        alpha = int(245 * ((y - (bh - grad_h)) / grad_h))
        draw_ov.line([(0, y), (bw, y)], fill=(0, 0, 0, max(0, min(255, alpha))))
    
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=5 * sf))
    img_hd = Image.alpha_composite(img_hd.convert("RGBA"), overlay)
    draw_hd = ImageDraw.Draw(img_hd)
    
    font_path = baixar_fonte()
    
    # 3. Selo Dinâmico Premium
    badge_h = int(bh * 0.05)
    f_badge = ImageFont.truetype(font_path, int(badge_h * 0.75)) if font_path else ImageFont.load_default()
    txt_badge = tag_texto
    bbox_b = draw_hd.textbbox((0,0), txt_badge, font=f_badge)
    badge_w = (bbox_b[2] - bbox_b[0]) + (40 * sf)
    
    # Selo Centralizado
    bx1, by1 = 30*sf, 40*sf
    bx2, by2 = bx1 + badge_w, by1 + badge_h
    draw_hd.rectangle([bx1, by1, bx2, by2], fill=MAIN_COLOR)
    draw_hd.text(((bx1 + bx2)//2, (by1 + by2)//2), txt_badge, font=f_badge, fill=(255, 255, 255), anchor="mm")

    texto_puro = limpar_emojis(texto)
    f_size = int(bh * 0.10) # Ligeiramente maior para títulos curtos
    font = ImageFont.truetype(font_path, f_size) if font_path else ImageFont.load_default()
    
    # GARANTE 1 LINHA (sem wrap)
    l = texto_puro.strip()
    bb = draw_hd.textbbox((0, 0), l, font=font)
    lw, lh = bb[2] - bb[0], bb[3] - bb[1]
    
    # Se ainda for muito grande (raro com 3 palavras), reduz a fonte
    if lw > (bw - 100*sf):
        f_size = int(f_size * (bw - 100*sf) / lw)
        font = ImageFont.truetype(font_path, f_size) if font_path else ImageFont.load_default()
        bb = draw_hd.textbbox((0, 0), l, font=font)
        lw, lh = bb[2] - bb[0], bb[3] - bb[1]

    tx = (bw - lw) // 2
    padding = 35 * sf
    ty = int(bh * 0.82) - lh
    
    # 4. Fundo do Título (Box)
    tx1, ty1 = tx - padding, ty - padding
    tx2, ty2 = tx + lw + padding, ty + lh + padding
    temp_box = Image.new("RGBA", (bw, bh), (0,0,0,0))
    draw_box = ImageDraw.Draw(temp_box)
    draw_box.rectangle([tx1, ty1, tx2, ty2], fill=MAIN_COLOR)
    img_hd = Image.alpha_composite(img_hd, temp_box)
    
    # Centro do box para ancoragem
    cx, cy = (tx1 + tx2) // 2, (ty1 + ty2) // 2
    
    # 5. Camada de Sombras Suaves (Drop Shadows)
    shadow_layer = Image.new("RGBA", (bw, bh), (0,0,0,0))
    s_draw = ImageDraw.Draw(shadow_layer)
    s_draw.text((cx + 4*sf, cy + 4*sf), l, font=font, fill=(0,0,0,200), anchor="mm")
    
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=3 * sf))
    img_hd = Image.alpha_composite(img_hd, shadow_layer)
    
    # 6. Desenhar Texto Principal (Nítido)
    draw_hd = ImageDraw.Draw(img_hd)
    draw_hd.text((cx, cy), l, font=font, fill=(255, 255, 255), anchor="mm")
        
    # 7. Ícone PREMIUM (Centralizado)
    try:
        emoji_url = f"https://raw.githubusercontent.com/iamcal/emoji-data/master/img-apple-160/{emoji_hex}.png"
        r_emoji = requests.get(emoji_url, timeout=10)
        if r_emoji.status_code == 200:
            emoji_img = Image.open(BytesIO(r_emoji.content)).convert("RGBA")
            e_size = int(f_size * 1.5)
            emoji_img = emoji_img.resize((e_size, e_size), Image.Resampling.LANCZOS)
            ix = (bw - e_size) // 2
            iy = ty - e_size - (20 * sf)
            
            # Sombra do Ícone
            e_shadow = Image.new("RGBA", (bw, bh), (0,0,0,0))
            ImageDraw.Draw(e_shadow).ellipse([ix+8*sf, iy+8*sf, ix+e_size+8*sf, iy+e_size+8*sf], fill=(0,0,0,150))
            e_shadow = e_shadow.filter(ImageFilter.GaussianBlur(radius=8*sf))
            img_hd = Image.alpha_composite(img_hd, e_shadow)
            img_hd.paste(emoji_img, (ix, iy), emoji_img)
    except Exception as e:
        log.warning(f"Erro ao carregar emoji: {e}")

    # 8. CTA Dinâmico (Sombra projetada)
    f_sub_size = int(badge_h * 0.75)
    f_sub = ImageFont.truetype(font_path, f_sub_size) if font_path else ImageFont.load_default()
    cta_t = 'Clique em "...mais" para ver na íntegra'
    bw_cta = draw_hd.textbbox((0,0), cta_t, font=f_sub)
    cx = (bw - (bw_cta[2]-bw_cta[0]))//2
    cy = bh - (65 * sf) # Mais espaço no 1:1
    
    cta_shadow = Image.new("RGBA", (bw, bh), (0,0,0,0))
    ImageDraw.Draw(cta_shadow).text((cx + 2*sf, cy + 2*sf), cta_t, font=f_sub, fill=(0,0,0,220))
    cta_shadow = cta_shadow.filter(ImageFilter.GaussianBlur(radius=2*sf))
    img_hd = Image.alpha_composite(img_hd, cta_shadow)
    
    draw_hd.text((cx, cy), cta_t, font=f_sub, fill=(255, 215, 0))

    # --- FINALIZAÇÃO: REDUÇÃO PARA 1080x1080 PADRÃO ---
    final_img = img_hd.resize((target_side, target_side), Image.Resampling.LANCZOS).convert("RGB")
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
                        
                        # FIX 403: baixar imagem dentro da sessão autenticada do Playwright
                        img_bytes = None
                        if img:
                            try:
                                resp = page.request.get(img)
                                if resp.status == 200:
                                    img_bytes = resp.body()
                                    log.info(f"🖼️ Imagem baixada via Playwright ({len(img_bytes)//1024}KB)")
                                else:
                                    log.warning(f"⚠️ Status imagem: {resp.status} para {img}")
                            except Exception as e_img:
                                log.warning(f"⚠️ Erro baixando imagem via Playwright: {e_img}")
                        
                        res.append({"id": make_article_id(link), "title": title, "link": link, "img": img, "img_bytes": img_bytes})
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
    
    for n in news:
        if n["id"] in posted:
            log.info(f"⏭️ Pulando: {n['title'][:50]}... (Já postado)")
            continue
        try:
            # Usar bytes baixados via Playwright (evita 403) ou fallback por URL
            img_data = n.get("img_bytes")
            if img_data is None:
                if not n.get("img"):
                    log.warning(f"⚠️ Sem imagem para: {n['title'][:50]}")
                    continue
                r_img = requests.get(n["img"], headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
                if r_img.status_code != 200:
                    log.warning(f"⚠️ Imagem retornou {r_img.status_code}, pulando.")
                    continue
                img_data = r_img.content
            
            estetica = gerar_gancho(n["title"])
            img_b = adicionar_texto_premium(img_data, estetica)
            
            padding = "\n.\n.\n.\n.\n.\n"
            msg = f"😱 {n['title'].upper()} 😱\n\nNotícia urgente! Veja os detalhes chocantes agora... 💣🔥\n{padding}🔗 LINK: {n['link']}"
            
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
                break
            else:
                log.error(f"Erro FB: {resp_data}")
        except Exception as e: 
            log.error(f"Erro no loop principal: {e}")
            log.error(traceback.format_exc())

if __name__ == "__main__": main()
