#!/usr/bin/env python3
"""
publicar_local.py — Publicação local de TESTE
Objetivo: validar token, página e geração de imagem SEM depender do GitHub Actions.
Executar: python publicar_local.py
"""

import os
import sys
import json
import re
import requests
import traceback
from io import BytesIO
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

load_dotenv(override=True)

# ─── CONFIGURAÇÃO ───────────────────────────────────────────────────────────
FB_PAGE_ID  = os.environ.get("FB_PAGE_ID", "").strip()
FB_TOKEN    = os.environ.get("FB_TOKEN", "").strip()
GEMINI_KEY  = os.environ.get("GEMINI_API_KEY", "").strip()
SFY_EMAIL   = os.environ.get("SFY_EMAIL", "").strip()
SFY_PASSWORD= os.environ.get("SFY_PASSWORD", "").strip()
FB_GRAPH    = "https://graph.facebook.com/v22.0"

# ─── PASSO 1: VERIFICAR TOKEN E PÁGINA ──────────────────────────────────────
def verificar_token():
    print("\n" + "="*60)
    print("PASSO 1: Verificando token e página...")
    print("="*60)
    print(f"  PAGE_ID : {FB_PAGE_ID}")
    print(f"  TOKEN   : {FB_TOKEN[:30]}..." if FB_TOKEN else "  TOKEN   : ❌ VAZIO!")

    if not FB_TOKEN or not FB_PAGE_ID:
        print("\n❌ ERRO: FB_TOKEN ou FB_PAGE_ID não encontrados no .env!")
        sys.exit(1)

    url = f"{FB_GRAPH}/{FB_PAGE_ID}?fields=id,name,link&access_token={FB_TOKEN}"
    r = requests.get(url, timeout=15)
    data = r.json()

    if "error" in data:
        err = data["error"]
        print(f"\n❌ ERRO DA API FACEBOOK:")
        print(f"   Código  : {err.get('code')}")
        print(f"   Mensagem: {err.get('message')}")
        print(f"   Tipo    : {err.get('type')}")
        print("\n💡 Dica: O token provavelmente expirou. Precisamos renovar.")
        sys.exit(1)

    nome_pagina = data.get("name", "desconhecido")
    print(f"\n✅ Token VÁLIDO!")
    print(f"   Página: {nome_pagina}")
    print(f"   ID    : {data.get('id')}")
    print(f"   Link  : {data.get('link', 'N/A')}")
    return nome_pagina

# ─── PASSO 2: BUSCAR NOTÍCIA VIA PLAYWRIGHT ─────────────────────────────────
def buscar_noticia():
    print("\n" + "="*60)
    print("PASSO 2: Buscando notícia via SharesForYou...")
    print("="*60)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright não instalado. Usando notícia de fallback.")
        return _noticia_fallback()

    noticia = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://www.sharesforyou.com/login", timeout=30000)
            page.fill("input[name='email']", SFY_EMAIL)
            page.fill("input[name='password']", SFY_PASSWORD)
            page.click("button[type='submit']")
            page.wait_for_url("**/dashboard**", timeout=40000)
            page.goto("https://www.sharesforyou.com/dashboard/share")
            page.wait_for_timeout(7000)

            try:
                page.click("button.change-order-by:has-text('Sharesforyou')", timeout=10000)
                page.wait_for_timeout(8000)
            except:
                pass

            cards = page.locator(".card").all()
            print(f"  Encontrados {len(cards)} cards.")

            for card in cards:
                try:
                    title = card.locator("h5, p.fs-4").first.inner_text().strip()
                    link  = card.locator("a:has(i.ti-eye)").first.get_attribute("href")
                    img   = card.locator("img").first.get_attribute("src")
                    if title and link:
                        if link.startswith("/"): link = "https://www.sharesforyou.com" + link
                        if img and img.startswith("/"): img = "https://www.sharesforyou.com" + img

                        # Baixar imagem DENTRO da sessão autenticada do Playwright
                        img_bytes = None
                        if img:
                            try:
                                resp = page.request.get(img)
                                if resp.status == 200:
                                    img_bytes = resp.body()
                                    print(f"  ✅ Imagem baixada via Playwright ({len(img_bytes)//1024}KB)")
                                else:
                                    print(f"  ⚠️ Status imagem: {resp.status}. Tentando com User-Agent...")
                            except Exception as e_img:
                                print(f"  ⚠️ Erro baixando imagem: {e_img}")

                        noticia = {"title": title, "link": link, "img": img, "img_bytes": img_bytes}
                        print(f"  ✅ Notícia encontrada: {title[:70]}")
                        break
                except:
                    continue

            browser.close()
    except Exception as e:
        print(f"  ⚠️ Erro no Playwright: {e}")
        print("  Usando notícia de fallback para o teste...")
        return _noticia_fallback()

    if not noticia:
        print("  Nenhuma notícia encontrada. Usando fallback.")
        return _noticia_fallback()

    return noticia

def _noticia_fallback():
    """Notícia de fallback para quando o Playwright falha — apenas para teste de publicação."""
    # Usa imagem pública do G1 para teste
    try:
        r = requests.get(
            "https://s2.glbimg.com/NuvnIQ5PUxkS8CjVoFgR7sUqTHk=/0x0:5000x3333/984x0/smart/filters:strip_icc()/i.s3.glbimg.com/v1/AUTH_59edd422c0c84a879bd37670ae4f538a/internal_photos/bs/2024/f/a/OEkPZRTvOo6rg8fjOIOA/gettyimages-2182419826.jpg",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15
        )
        img_bytes = r.content if r.status_code == 200 else None
    except:
        img_bytes = None
    return {
        "title": "Teste de Publicação Local — Bot de Notícias",
        "link": "https://g1.globo.com",
        "img": "https://g1.globo.com",
        "img_bytes": img_bytes,
    }

# ─── PASSO 3: GERAR GANCHO COM GEMINI ───────────────────────────────────────
def emoji_to_hex(emoji_char):
    if not emoji_char: return None
    try:
        hex_parts = []
        for char in emoji_char:
            h = f"{ord(char):x}"
            if h != "fe0f":
                hex_parts.append(h)
        return "-".join(hex_parts)
    except:
        return None

def gerar_gancho(title):
    print("\n" + "="*60)
    print("PASSO 3: Gerando gancho visual com Gemini...")
    print("="*60)

    default = {"hook": "REVELAÇÃO CHOCANTE!", "tag": "NOTÍCIA URGENTE", "color": (255, 0, 0, 200), "emoji": "1f6a8", "reactions": []}

    if not GEMINI_KEY:
        print("  ⚠️ GEMINI_KEY não encontrada. Usando padrão.")
        return default

    CATEGORIES = {
        "URGENTE": {"tag": "NOTÍCIA URGENTE", "color": (255, 0, 0, 200)},
        "POLITICA": {"tag": "NA POLÍTICA", "color": (0, 102, 255, 200)},
        "ESPORTE":  {"tag": "NO ESPORTE", "color": (50, 205, 50, 200)},
        "FOFOCA":   {"tag": "VOCÊ NÃO VAI ACREDITAR", "color": (255, 215, 0, 200)},
        "CRIME":    {"tag": "CRIME AGORA", "color": (0, 0, 0, 200)},
    }

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}"
        prompt = (
            f'Analise a notícia: "{title}".\n'
            f"Retorne APENAS uma linha: HOOK | CATEGORY | EMOJI | REACTION_DATA\n"
            f"- HOOK: título MÁXIMO 3 PALAVRAS em MAIÚSCULAS.\n"
            f"- CATEGORY: URGENTE, POLITICA, ESPORTE, FOFOCA, CRIME.\n"
            f"- EMOJI: um único emoji para o tema.\n"
            f"- REACTION_DATA: 3 reações curtas no formato E1:TEXTO1,E2:TEXTO2,E3:TEXTO3\n"
            f"  Ex: 😱:Absurdo!,😢:Que triste,🙌:Justiça!"
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        r = requests.post(url, json=payload, timeout=15)
        r.raise_for_status()
        raw = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

        if "|" in raw:
            parts = [p.strip() for p in raw.split("|")]
            if len(parts) >= 4:
                hook     = parts[0].replace('"', '').upper()
                cat_key  = parts[1].upper()
                emoji_ch = parts[2]
                react_raw = parts[3]

                # Parse dynamic reactions
                reactions = []
                for r_item in react_raw.split(","):
                    if ":" in r_item:
                        e_char, r_text = r_item.split(":", 1)
                        e_hex = emoji_to_hex(e_char.strip())
                        if e_hex:
                            reactions.append((e_hex, r_text.strip()))

                config = CATEGORIES.get(cat_key, CATEGORIES["URGENTE"])
                e_hex  = emoji_to_hex(emoji_ch) or "1f525"
                print(f"  ✅ Hook: {hook} | Tag: {config['tag']} | Reactions: {len(reactions)}")
                return {"hook": hook, "tag": config["tag"], "color": config["color"], "emoji": e_hex, "reactions": reactions[:3]}
    except Exception as e:
        print(f"  ⚠️ Erro Gemini: {e}")

    return default

# ─── PASSO 4: GERAR IMAGEM ───────────────────────────────────────────────────
def limpar_emojis(texto):
    return re.sub(r'[^\w\s.,!?;:\"\'()\-\u00C0-\u00FF]+', '', texto).strip()

def gerar_imagem(img_bytes_ou_url, dados):
    print("\n" + "="*60)
    print("PASSO 4: Gerando imagem premium...")
    print("="*60)

    if isinstance(img_bytes_ou_url, bytes):
        # Já temos os bytes, usar direto
        img_raw = img_bytes_ou_url
    else:
        # Tentar baixar com User-Agent como fallback
        r = requests.get(img_bytes_ou_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        if r.status_code != 200:
            raise Exception(f"Não foi possível baixar imagem: status {r.status_code}")
        img_raw = r.content

    MAIN_COLOR = dados["color"]
    texto      = dados["hook"]
    tag_texto  = dados["tag"]
    emoji_hex  = dados["emoji"]

    img = Image.open(BytesIO(img_raw)).convert("RGB")
    w, h = img.size
    side = min(w, h)
    img_sq = img.crop(((w-side)//2, (h-side)//2, (w+side)//2, (h+side)//2))

    sf, target = 2, 1080
    bw = bh = target * sf
    img_hd = img_sq.resize((bw, bh), Image.Resampling.LANCZOS)
    img_hd = ImageEnhance.Color(img_hd).enhance(1.3)
    img_hd = ImageEnhance.Contrast(img_hd).enhance(1.1)
    img_hd = ImageEnhance.Sharpness(img_hd).enhance(1.4)

    overlay = Image.new("RGBA", (bw, bh), (0,0,0,0))
    draw_ov = ImageDraw.Draw(overlay)
    grad_h  = int(bh * 0.70)
    for y in range(bh - grad_h, bh):
        alpha = int(245 * ((y - (bh - grad_h)) / grad_h))
        draw_ov.line([(0, y), (bw, y)], fill=(0, 0, 0, max(0, min(255, alpha))))
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=5*sf))
    img_hd  = Image.alpha_composite(img_hd.convert("RGBA"), overlay)
    draw_hd = ImageDraw.Draw(img_hd)

    # Fonte
    font_path = None
    for f in ["fonts/impact.ttf", "C:\\Windows\\Fonts\\impact.ttf",
              "fonts/NotoSans-Bold.ttf", "C:\\Windows\\Fonts\\arialbd.ttf"]:
        if os.path.exists(f):
            font_path = f
            break

    # Selo
    badge_h = int(bh * 0.05)
    f_badge = ImageFont.truetype(font_path, int(badge_h * 0.75)) if font_path else ImageFont.load_default()
    bb      = draw_hd.textbbox((0,0), tag_texto, font=f_badge)
    badge_w = (bb[2]-bb[0]) + 40*sf
    bx1, by1 = 30*sf, 40*sf
    bx2, by2 = bx1+badge_w, by1+badge_h
    draw_hd.rectangle([bx1, by1, bx2, by2], fill=MAIN_COLOR)
    draw_hd.text(((bx1+bx2)//2, (by1+by2)//2), tag_texto, font=f_badge, fill=(255,255,255), anchor="mm")

    # Título
    texto_puro = limpar_emojis(texto)
    f_size = int(bh * 0.10)
    font   = ImageFont.truetype(font_path, f_size) if font_path else ImageFont.load_default()
    l      = texto_puro.strip()
    bb     = draw_hd.textbbox((0,0), l, font=font)
    lw, lh = bb[2]-bb[0], bb[3]-bb[1]
    if lw > (bw - 100*sf):
        f_size = int(f_size * (bw - 100*sf) / lw)
        font   = ImageFont.truetype(font_path, f_size) if font_path else ImageFont.load_default()
        bb     = draw_hd.textbbox((0,0), l, font=font)
        lw, lh = bb[2]-bb[0], bb[3]-bb[1]

    tx = (bw-lw)//2
    pad = 35*sf
    ty  = int(bh * 0.82) - lh
    tx1, ty1 = tx-pad, ty-pad
    tx2, ty2 = tx+lw+pad, ty+lh+pad

    box = Image.new("RGBA", (bw, bh), (0,0,0,0))
    ImageDraw.Draw(box).rectangle([tx1, ty1, tx2, ty2], fill=MAIN_COLOR)
    img_hd = Image.alpha_composite(img_hd, box)
    cx, cy = (tx1+tx2)//2, (ty1+ty2)//2

    shadow = Image.new("RGBA", (bw, bh), (0,0,0,0))
    ImageDraw.Draw(shadow).text((cx+4*sf, cy+4*sf), l, font=font, fill=(0,0,0,200), anchor="mm")
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=3*sf))
    img_hd = Image.alpha_composite(img_hd, shadow)

    draw_hd = ImageDraw.Draw(img_hd)
    draw_hd.text((cx, cy), l, font=font, fill=(255,255,255), anchor="mm")

    # Emoji
    try:
        e_url = f"https://raw.githubusercontent.com/iamcal/emoji-data/master/img-apple-160/{emoji_hex}.png"
        re_e  = requests.get(e_url, timeout=10)
        if re_e.status_code == 200:
            ei    = Image.open(BytesIO(re_e.content)).convert("RGBA")
            e_sz  = int(f_size * 1.5)
            ei    = ei.resize((e_sz, e_sz), Image.Resampling.LANCZOS)
            ix, iy = (bw-e_sz)//2, ty1 - e_sz - 20*sf
            es = Image.new("RGBA", (bw, bh), (0,0,0,0))
            ImageDraw.Draw(es).ellipse([ix+8*sf, iy+8*sf, ix+e_sz+8*sf, iy+e_sz+8*sf], fill=(0,0,0,150))
            es = es.filter(ImageFilter.GaussianBlur(radius=8*sf))
            img_hd = Image.alpha_composite(img_hd, es)
            img_hd.paste(ei, (ix, iy), ei)
    except Exception as e:
        print(f"  ⚠️ Emoji não carregado: {e}")

    # Reações
    reactions = dados.get("reactions", [])
    if reactions:
        render_y = ty2 + int(60 * sf)
        r_emoji_size = int(bh * 0.05)
        f_react_size = int(bh * 0.025)
        f_react = ImageFont.truetype(font_path, f_react_size) if font_path else ImageFont.load_default()

        gap = int(40 * sf)
        sp = int(10 * sf)
        items = []
        tot_w = 0
        
        for (r_hex, r_text) in reactions:
            lbb = draw_hd.textbbox((0, 0), r_text, font=f_react)
            lw_r = lbb[2] - lbb[0]
            item_w = r_emoji_size + sp + lw_r
            items.append({"hex": r_hex, "text": r_text, "w": item_w})
            tot_w += item_w
        
        tot_w += gap * (len(reactions) - 1)
        rx = (bw - tot_w) // 2

        for item in items:
            try:
                r_url = f"https://raw.githubusercontent.com/iamcal/emoji-data/master/img-facebook-96/{item['hex']}.png"
                r_res = requests.get(r_url, timeout=5)
                if r_res.status_code != 200:
                    r_url = f"https://raw.githubusercontent.com/iamcal/emoji-data/master/img-apple-160/{item['hex']}.png"
                    r_res = requests.get(r_url, timeout=5)
                
                if r_res.status_code == 200:
                    ri = Image.open(BytesIO(r_res.content)).convert("RGBA")
                    ri = ri.resize((r_emoji_size, r_emoji_size), Image.Resampling.LANCZOS)
                    img_hd.paste(ri, (rx, render_y), ri)
                    
                    tx_p = rx + r_emoji_size + sp
                    ty_p = render_y + (r_emoji_size // 2)
                    
                    draw_hd.text((tx_p + 1*sf, ty_p + 1*sf), item["text"], font=f_react, fill=(0, 0, 0, 180), anchor="lm")
                    draw_hd.text((tx_p, ty_p), item["text"], font=f_react, fill=(255, 255, 255), anchor="lm")
                    
                    rx += item["w"] + gap
            except:
                pass

    # CTA
    f_sub = ImageFont.truetype(font_path, int(badge_h*0.75)) if font_path else ImageFont.load_default()
    cta_t = 'Clique em "...mais" para ver na íntegra'
    draw_hd = ImageDraw.Draw(img_hd)
    bw_cta = draw_hd.textbbox((0,0), cta_t, font=f_sub)
    cx_cta = (bw-(bw_cta[2]-bw_cta[0]))//2
    cy_cta = bh - 65*sf
    cta_s  = Image.new("RGBA", (bw, bh), (0,0,0,0))
    ImageDraw.Draw(cta_s).text((cx_cta+2*sf, cy_cta+2*sf), cta_t, font=f_sub, fill=(0,0,0,220))
    cta_s = cta_s.filter(ImageFilter.GaussianBlur(radius=2*sf))
    img_hd = Image.alpha_composite(img_hd, cta_s)
    ImageDraw.Draw(img_hd).text((cx_cta, cy_cta), cta_t, font=f_sub, fill=(255,215,0))

    final = img_hd.resize((target, target), Image.Resampling.LANCZOS).convert("RGB")
    out   = BytesIO()
    final.save(out, format="JPEG", quality=98)

    # Salvar cópia local para conferência
    final.save("preview_publicacao.jpg")
    print("  ✅ Imagem gerada e salva como preview_publicacao.jpg")

    return out.getvalue()

# ─── PASSO 5: PUBLICAR NO FACEBOOK ──────────────────────────────────────────
def publicar(noticia, img_bytes):
    print("\n" + "="*60)
    print("PASSO 5: Publicando no Facebook...")
    print("="*60)

    padding = "\n.\n.\n.\n.\n.\n"
    msg = (
        f"😱 {noticia['title'].upper()} 😱\n\n"
        f"Notícia urgente! Veja os detalhes chocantes agora... 💣🔥"
        f"{padding}"
        f"🔗 LINK: {noticia['link']}"
    )

    r = requests.post(
        f"{FB_GRAPH}/{FB_PAGE_ID}/photos",
        files={"source": ("foto.jpg", img_bytes, "image/jpeg")},
        data={"message": msg, "access_token": FB_TOKEN, "published": "true"},
        timeout=60
    )
    data = r.json()

    if "error" in data:
        err = data["error"]
        print(f"\n❌ ERRO AO PUBLICAR:")
        print(f"   Código  : {err.get('code')}")
        print(f"   Mensagem: {err.get('message')}")
        print(f"   Tipo    : {err.get('type')}")
        return None

    post_id = data.get("id", "")
    # O ID retornado vem no formato PAGEID_POSTID
    parts = post_id.split("_")
    link_post = f"https://www.facebook.com/{FB_PAGE_ID}/posts/{parts[-1]}" if len(parts) > 1 else f"https://www.facebook.com/{FB_PAGE_ID}"

    print(f"\n✅ PUBLICADO COM SUCESSO!")
    print(f"   ID do Post: {post_id}")
    print(f"   🔗 LINK DIRETO: {link_post}")
    return link_post

# ─── MAIN ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "--- "*20)
    print("  BOT NOTÍCIAS — PUBLICAÇÃO LOCAL DE TESTE")
    print("--- "*20)

    try:
        nome_pagina = verificar_token()

        print(f"\n⚠️  Você está prestes a publicar na página: '{nome_pagina}'")
        print("   Pressione ENTER para continuar ou CTRL+C para cancelar...")
        input()

        noticia = buscar_noticia()
        print(f"\n  📰 Notícia: {noticia['title'][:80]}")
        print(f"  🔗 Link   : {noticia['link']}")

        gancho  = gerar_gancho(noticia["title"])
        img_fonte = noticia.get("img_bytes") or noticia["img"]
        img_bytes = gerar_imagem(img_fonte, gancho)
        link    = publicar(noticia, img_bytes)

        if link:
            print("\n" + "="*60)
            print("✅ TUDO CONCLUÍDO!")
            print(f"   Abra o link e confirme a publicação:")
            print(f"   {link}")
            print("="*60)
        else:
            print("\n❌ Publicação falhou. Veja os erros acima.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⛔ Cancelado pelo usuário.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}")
        traceback.print_exc()
        sys.exit(1)
