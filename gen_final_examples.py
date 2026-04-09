import os
import textwrap
import requests
import random
import re
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# Funções idênticas ao bot.py final
def baixar_fonte(emoji=False):
    if emoji:
        for f in ["C:\\Windows\\Fonts\\seguiemj.ttf"]:
            if os.path.exists(f): return f
    # Priorizar Impact para alto impacto
    for f in ["C:\\Windows\\Fonts\\impact.ttf", "C:\\Windows\\Fonts\\ariblk.ttf", "fonts/NotoSans-Bold.ttf", "C:\\Windows\\Fonts\\arialbd.ttf"]:
        if os.path.exists(f): return f
    return None

def limpar_emojis(texto):
    # Preserva caracteres acentuados (Latin-1) e pontuação comum
    return re.sub(r'[^\w\s.,!?;:\"\'\(\)\-\u00C0-\u00FF]+', '', texto).strip()

def adicionar_texto_refined(img_bytes, texto):
    # Paleta de Cores Noticiário
    PALETTES = [
        (220, 20, 60, 170), (0, 51, 153, 170), (15, 15, 15, 170)
    ]
    MAIN_COLOR = random.choice(PALETTES)
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

    # 2. Gradiente de Base 
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
    
    # 3. Selo URGENTE Premium
    badge_h = int(bh * 0.05)
    f_badge = ImageFont.truetype(font_path, int(badge_h * 0.75)) if font_path else ImageFont.load_default()
    txt_badge = "NOTÍCIA URGENTE"
    bbox_b = draw_hd.textbbox((0,0), txt_badge, font=f_badge)
    badge_w = (bbox_b[2] - bbox_b[0]) + (40 * sf)
    # Selo Centralizado
    bx1, by1 = 30*sf, 40*sf
    bx2, by2 = bx1 + badge_w, by1 + badge_h
    draw_hd.rectangle([bx1, by1, bx2, by2], fill=(220, 20, 60, 255))
    draw_hd.text(((bx1 + bx2)//2, (by1 + by2)//2), txt_badge, font=f_badge, fill=(255, 255, 255), anchor="mm")

    texto_puro = limpar_emojis(texto)
    f_size = int(bh * 0.10) 
    font = ImageFont.truetype(font_path, f_size) if font_path else ImageFont.load_default()
    
    l = texto_puro.strip()
    bb = draw_hd.textbbox((0, 0), l, font=font)
    lw, lh = bb[2] - bb[0], bb[3] - bb[1]
    
    if lw > (bw - 100*sf):
        f_size = int(f_size * (bw - 100*sf) / lw)
        font = ImageFont.truetype(font_path, f_size) if font_path else ImageFont.load_default()
        bb = draw_hd.textbbox((0, 0), l, font=font)
        lw, lh = bb[2] - bb[0], bb[3] - bb[1]

    tx = (bw - lw) // 2
    padding = 35 * sf
    ty = int(bh * 0.82) - lh
    
    # 4. Box de Título
    tx1, ty1 = tx - padding, ty - padding
    tx2, ty2 = tx + lw + padding, ty + lh + padding
    temp_box = Image.new("RGBA", (bw, bh), (0,0,0,0))
    draw_box = ImageDraw.Draw(temp_box)
    draw_box.rectangle([tx1, ty1, tx2, ty2], fill=MAIN_COLOR)
    img_hd = Image.alpha_composite(img_hd, temp_box)
    
    # Centro para ancoragem
    cx, cy = (tx1 + tx2) // 2, (ty1 + ty2) // 2
    
    # 5. Sombras Suaves
    shadow_layer = Image.new("RGBA", (bw, bh), (0,0,0,0))
    s_draw = ImageDraw.Draw(shadow_layer)
    s_draw.text((cx + 4*sf, cy + 4*sf), l, font=font, fill=(0,0,0,200), anchor="mm")
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=3 * sf))
    img_hd = Image.alpha_composite(img_hd, shadow_layer)
    
    # 6. Texto Principal
    draw_hd = ImageDraw.Draw(img_hd)
    draw_hd.text((cx, cy), l, font=font, fill=(255, 255, 255), anchor="mm")

    # 7. Ícone
    try:
        icons = ["🚨", "💀", "🔥", "💣", "⚠️"]
        char = random.choice(icons)
        EMOJI_MAP = {"🚨": "1f6a8", "💀": "1f480", "🔥": "1f525", "💣": "1f4a3", "⚠️": "26a0"}
        hex_code = EMOJI_MAP.get(char, "1f480")
        emoji_url = f"https://raw.githubusercontent.com/iamcal/emoji-data/master/img-apple-160/{hex_code}.png"
        r_emoji = requests.get(emoji_url, timeout=10)
        if r_emoji.status_code == 200:
            emoji_img = Image.open(BytesIO(r_emoji.content)).convert("RGBA")
            e_size = int(f_size * 1.5)
            emoji_img = emoji_img.resize((e_size, e_size), Image.Resampling.LANCZOS)
            ix = (bw - e_size) // 2
            iy = ty - e_size - (20 * sf)
            e_shadow = Image.new("RGBA", (bw, bh), (0,0,0,0))
            ImageDraw.Draw(e_shadow).ellipse([ix+8*sf, iy+8*sf, ix+e_size+8*sf, iy+e_size+8*sf], fill=(0,0,0,150))
            e_shadow = e_shadow.filter(ImageFilter.GaussianBlur(radius=8*sf))
            img_hd = Image.alpha_composite(img_hd, e_shadow)
            img_hd.paste(emoji_img, (ix, iy), emoji_img)
    except: pass

    # 8. CTA Dinâmico (Sombra projetada)
    f_sub_size = int(badge_h * 0.75)
    f_sub = ImageFont.truetype(font_path, f_sub_size) if font_path else ImageFont.load_default()
    cta_t = 'Clique em "...mais" para ver na íntegra'
    bw_cta = draw_hd.textbbox((0,0), cta_t, font=f_sub)
    cx = (bw - (bw_cta[2]-bw_cta[0]))//2
    cy = bh - (65 * sf)
    cta_shadow = Image.new("RGBA", (bw, bh), (0,0,0,0))
    ImageDraw.Draw(cta_shadow).text((cx + 2*sf, cy + 2*sf), cta_t, font=f_sub, fill=(0,0,0,220))
    cta_shadow = cta_shadow.filter(ImageFilter.GaussianBlur(radius=2*sf))
    img_hd = Image.alpha_composite(img_hd, cta_shadow)
    draw_hd.text((cx, cy), cta_t, font=f_sub, fill=(255, 215, 0))

    final_img = img_hd.resize((target_side, target_side), Image.Resampling.LANCZOS).convert("RGB")
    return final_img

if __name__ == "__main__":
    url = "https://picsum.photos/1024/576"
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
        img_bytes = r.content
        texto = "OUÇA ESTA REVELAÇÃO AGORA! 😱💀"
        for i in range(3):
            out_img = adicionar_texto_refined(img_bytes, texto)
            out_img.save(f"absolute_final_{i}.jpg", quality=98)
            print(f"Versão absoluta {i} gerada.")
    except Exception as e:
        print(f"Erro: {e}")
