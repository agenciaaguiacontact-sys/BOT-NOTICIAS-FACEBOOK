#!/usr/bin/env python3
"""
SharesForYou → Facebook Auto-Poster Bot
Roda via GitHub Actions a cada 1 hora — sem custo, sem servidor.

Melhorias v2:
- Playwright para scraping real (site é SPA/JavaScript)
- Gemini Flash grátis substituiu Claude
- Anti-duplicata robusto por URL hash
- Controle de tamanho da imagem (<4MB para Meta API)
- Retry com backoff exponencial
- Logging estruturado
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

# Carregar variáveis de ambiente do arquivo .env (se existir)
load_dotenv()

# ──────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# CONFIGURAÇÕES (via GitHub Secrets)
# ──────────────────────────────────────────────
SFY_EMAIL    = os.environ["SFY_EMAIL"]
SFY_PASSWORD = os.environ["SFY_PASSWORD"]
FB_PAGE_ID   = os.environ["FB_PAGE_ID"]
FB_TOKEN     = os.environ["FB_TOKEN"]       # Page Access Token (longa duração)
GEMINI_KEY   = os.environ.get("GEMINI_API_KEY", "")  # Google AI Studio — grátis

POSTED_FILE  = "posted_ids.json"            # salvo no repositório via git commit
SFY_SHARE    = "https://www.sharesforyou.com/dashboard/share"  # URL real das notícias (SPA)
SFY_LOGIN    = "https://www.sharesforyou.com"
FB_GRAPH     = "https://graph.facebook.com/v25.0"  # ← Versão atualizada (era v21.0)

MAX_IMG_BYTES = 3_500_000  # 3.5MB — margem abaixo do limite de 4MB da Meta API

# Paletas de cores chamativas para o texto (rotaciona)
COLOR_PALETTES = [
    {"bg": (220, 20, 60),  "text": (255, 255, 255)},   # vermelho + branco
    {"bg": (255, 140, 0),  "text": (0,   0,   0)},     # laranja + preto
    {"bg": (30,  30,  30), "text": (255, 215, 0)},     # preto + dourado
    {"bg": (0,   100, 200),"text": (255, 255, 255)},   # azul + branco
    {"bg": (50,  205, 50), "text": (0,   0,   0)},     # verde + preto
]


# ──────────────────────────────────────────────
# HTTP SESSION COM RETRY
# ──────────────────────────────────────────────
def make_session() -> requests.Session:
    """Cria sessão HTTP com retry automático em erros temporários."""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=2,            # espera 2s, 4s, 8s entre tentativas
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# ──────────────────────────────────────────────
# ANTI-DUPLICATA
# ──────────────────────────────────────────────
def load_posted() -> set:
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE) as f:
            return set(json.load(f))
    return set()


def save_posted(ids: set):
    """Salva no máximo os últimos 500 IDs para não crescer infinitamente."""
    ids_list = sorted(ids)[-500:]
    with open(POSTED_FILE, "w") as f:
        json.dump(ids_list, f, indent=2)


def make_article_id(url: str) -> str:
    """ID único e estável baseado na URL completa."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


# ──────────────────────────────────────────────
# UTILITÁRIOS
# ──────────────────────────────────────────────
def truncate_title(title: str, max_words: int = 7) -> str:
    """Corta o título para deixar curto e chamativo."""
    words = title.strip().split()
    if len(words) <= max_words:
        return title
    return " ".join(words[:max_words]) + "...Ver mais"


def palette_for(article_id: str) -> dict:
    idx = int(hashlib.md5(article_id.encode()).hexdigest(), 16) % len(COLOR_PALETTES)
    return COLOR_PALETTES[idx]


# ──────────────────────────────────────────────
# GERAR FRASE DE GANCHO COM GEMINI (gratuito)
# ──────────────────────────────────────────────
def gerar_gancho(title: str) -> str:
    """
    Usa Gemini Flash (gratuito) para criar frase curta e chamativa.
    Fallback automático se a chave não estiver configurada.

    Para obter GRÁTIS: https://aistudio.google.com/apikey
    Adicione o secret GEMINI_API_KEY no repositório GitHub.
    Limite gratuito: 1.500 requisições/dia — mais que suficiente.
    """
    if not GEMINI_KEY:
        words = title.split()[:6]
        return " ".join(words).upper() + "!"

    try:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models"
            "/gemini-2.5-flash:generateContent"
            f"?key={GEMINI_KEY}"
        )
        payload = {
            "contents": [{
                "parts": [{
                    "text": (
                        f"Crie UMA frase curta (máximo 8 palavras) em PORTUGUÊS "
                        f"para ser sobreposta em letras grandes numa foto de notícia. "
                        f"A frase deve ser um GANCHO muito chamativo que desperte "
                        f"curiosidade e vontade de clicar, relacionado ao título: "
                        f'"{title}". '
                        f"Responda APENAS a frase, sem aspas, sem pontuação no final."
                    )
                }]
            }],
            "generationConfig": {
                "maxOutputTokens": 60,
                "temperature": 0.9,
            }
        }
        r = requests.post(url, json=payload, timeout=20)
        r.raise_for_status()
        data = r.json()
        texto = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return texto.upper()
    except Exception as e:
        log.warning(f"Gemini API erro: {e}. Usando fallback.")
        words = title.split()[:6]
        return " ".join(words).upper() + "!"


# ──────────────────────────────────────────────
# PROCESSAMENTO DE IMAGEM
# ──────────────────────────────────────────────
def baixar_fonte() -> str:
    """Usa font local se existir na pasta fonts/, senão usa do sistema ou baixa."""
    # Verifica pasta fonts/ do projeto (melhor opção — determinístico)
    local = os.path.join(os.path.dirname(__file__), "fonts")
    for fname in os.listdir(local) if os.path.isdir(local) else []:
        if fname.lower().endswith((".ttf", ".otf")):
            return os.path.join(local, fname)

    # Fontes do sistema Ubuntu (GitHub Actions runner)
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c

    # Fallback: baixar NotoSans do Google Fonts (apenas uma vez por execução)
    url = "https://github.com/google/fonts/raw/main/ofl/notosans/NotoSans-Bold.ttf"
    dest = "/tmp/font_bold.ttf"
    if not os.path.exists(dest):
        log.info("Baixando fonte NotoSans-Bold...")
        r = requests.get(url, timeout=30)
        with open(dest, "wb") as f:
            f.write(r.content)
    return dest


def comprimir_imagem(img: Image.Image) -> bytes:
    """
    Salva imagem em JPEG com qualidade ajustável para caber em MAX_IMG_BYTES.
    Garante conformidade com o limite de 4MB da Meta API.
    """
    out = BytesIO()
    for quality in [92, 80, 70, 60, 50]:
        out.seek(0)
        out.truncate()
        img.save(out, format="JPEG", quality=quality)
        if out.tell() <= MAX_IMG_BYTES:
            log.info(f"Imagem comprimida: {out.tell() / 1024:.0f} KB (quality={quality})")
            return out.getvalue()
    # Se ainda estiver grande, reduz dimensão
    w, h = img.size
    img_small = img.resize((w // 2, h // 2), Image.LANCZOS)
    out.seek(0)
    out.truncate()
    img_small.save(out, format="JPEG", quality=70)
    log.warning(f"Imagem redimensionada para {w//2}x{h//2}")
    return out.getvalue()


def adicionar_texto_imagem(img_bytes: bytes, texto: str, palette: dict) -> bytes:
    """
    Abre imagem, adiciona faixa colorida no terço inferior com texto grande.
    Retorna bytes da imagem modificada em JPEG, respeitando o limite da API.
    """
    img = Image.open(BytesIO(img_bytes)).convert("RGB")
    w, h = img.size

    # Faixa = 35% da altura
    faixa_h = int(h * 0.35)
    faixa_y = h - faixa_h

    # Faixa semi-opaca
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    bg = palette["bg"]
    draw_ov.rectangle([(0, faixa_y), (w, h)], fill=(*bg, 220))
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay).convert("RGB")

    draw = ImageDraw.Draw(img)
    font_path = baixar_fonte()

    texto_wrapped = textwrap.fill(texto, width=20)
    tw, th = 0, 0
    font = ImageFont.load_default()
    for size in range(72, 20, -2):
        try:
            font = ImageFont.truetype(font_path, size)
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.multiline_textbbox((0, 0), texto_wrapped, font=font, spacing=8)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        if tw < w - 30 and th < faixa_h - 20:
            break

    tx = (w - tw) // 2
    ty = faixa_y + (faixa_h - th) // 2

    # Sombra
    for dx, dy in [(2, 2), (-2, 2), (2, -2), (-2, -2)]:
        draw.multiline_text((tx + dx, ty + dy), texto_wrapped, font=font,
                            fill=(0, 0, 0), spacing=8, align="center")

    # Texto principal
    draw.multiline_text((tx, ty), texto_wrapped, font=font,
                        fill=palette["text"], spacing=8, align="center")

    # Borda superior da faixa
    draw.line([(0, faixa_y), (w, faixa_y)], fill=palette["text"], width=4)

    return comprimir_imagem(img)


# ──────────────────────────────────────────────
# SCRAPING COM PLAYWRIGHT (suporta sites JavaScript/SPA)
# ──────────────────────────────────────────────
def get_noticias_playwright() -> list[dict]:
    """
    Faz login e extrai notícias usando Playwright.
    O SharesForYou é um SPA (React/Vue) — requests simples não funciona.

    URL real: https://www.sharesforyou.com/dashboard/share
    """
    from playwright.sync_api import sync_playwright

    noticias = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            # 1. Login
            log.info("Acessando SharesForYou para login...")
            page.goto("https://www.sharesforyou.com", timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)

            # Preenche credenciais
            page.fill("input[type='email'], input[name='email']", SFY_EMAIL)
            page.fill("input[type='password'], input[name='password']", SFY_PASSWORD)
            page.click("button[type='submit'], input[type='submit']")
            page.wait_for_load_state("networkidle", timeout=15000)
            
            # Debug: Capturar tela após login
            page.screenshot(path="debug_after_login.png")
            log.info(f"URL após login: {page.url}")

            # 2. Navega para a página de compartilhamento
            page.goto(SFY_SHARE, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=20000)
            
            # Debug: Capturar tela na página de notícias
            page.screenshot(path="debug_news_page.png")

            # Aguarda os cards carregarem
            page.wait_for_selector(
                ".card, [class*='card'], article, .news-item",
                timeout=15000
            )
            time.sleep(2)  # pequena pausa para JS finalizar

            log.info(f"Página carregada: {page.url}")

            # 3. Extrai dados dos cards
            cards = page.query_selector_all(".card, [class*='card'], article, .news-item")
            log.info(f"{len(cards)} cards encontrados no DOM.")

            seen_urls = set()
            for card in cards:
                try:
                    # Título
                    title_el = card.query_selector("h1, h2, h3, h4, h5, p, a")
                    if not title_el:
                        continue
                    title = title_el.inner_text().strip()
                    if len(title) < 10:
                        continue

                    # Imagem
                    img_el = card.query_selector("img")
                    img_url = ""
                    if img_el:
                        img_url = (img_el.get_attribute("src") or
                                   img_el.get_attribute("data-src") or "")

                    # Link de compartilhamento (ícone olho ou link principal)
                    share_link = ""
                    links = card.query_selector_all("a[href]")
                    for a in links:
                        href = a.get_attribute("href") or ""
                        if not href or href == "#":
                            continue
                        # Ícone de olho = link de visualização/compartilhamento
                        icon = a.query_selector("i, svg, .icon")
                        icon_class = ""
                        if icon:
                            icon_class = (icon.get_attribute("class") or "").lower()
                        if "eye" in icon_class or "view" in icon_class:
                            share_link = href
                            break
                        # Fallback: qualquer link de artigo
                        if any(k in href for k in ["/news/", "/article/", "/view/",
                                                    "/noticia/", "sharesforyou.com"]):
                            share_link = href

                    if not share_link:
                        # Usa o primeiro link do card como fallback
                        for a in links:
                            href = a.get_attribute("href") or ""
                            if href and href != "#":
                                share_link = href
                                break

                    if not share_link or share_link in seen_urls:
                        continue
                    seen_urls.add(share_link)

                    # URL absoluta
                    if share_link.startswith("/"):
                        share_link = "https://www.sharesforyou.com" + share_link
                    if img_url.startswith("/"):
                        img_url = "https://www.sharesforyou.com" + img_url

                    article_id = make_article_id(share_link)
                    noticias.append({
                        "id": article_id,
                        "title": title,
                        "share_link": share_link,
                        "img_url": img_url,
                    })

                except Exception as e:
                    log.debug(f"Erro ao processar card: {e}")
                    continue

        except Exception as e:
            log.error(f"Erro no Playwright: {e}")
        finally:
            browser.close()

    log.info(f"{len(noticias)} notícias extraídas.")
    return noticias


def get_image_from_article(noticia: dict) -> bytes | None:
    """Tenta baixar a imagem da notícia via requests simples."""
    session = make_session()

    # Tenta direto pela URL da imagem do card
    if noticia.get("img_url"):
        try:
            r = session.get(noticia["img_url"], timeout=15)
            if r.status_code == 200 and len(r.content) > 5000:
                return r.content
        except Exception as e:
            log.debug(f"Imagem do card indisponível: {e}")

    # Tenta buscar pelo artigo (HTML estático)
    try:
        from bs4 import BeautifulSoup
        r = session.get(noticia["share_link"], timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        # Open Graph image (mais confiável)
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            r2 = session.get(og["content"], timeout=15)
            if r2.status_code == 200:
                return r2.content
        # Imagem principal
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if any(k in src for k in ["logo", "icon", "avatar", "thumb"]):
                continue
            if src.startswith("http") or src.startswith("/"):
                if src.startswith("/"):
                    src = "https://www.sharesforyou.com" + src
                r3 = session.get(src, timeout=15)
                if r3.status_code == 200 and len(r3.content) > 5000:
                    return r3.content
    except Exception as e:
        log.debug(f"Erro ao buscar imagem do artigo: {e}")

    return None


# ──────────────────────────────────────────────
# PUBLICAR NO FACEBOOK
# ──────────────────────────────────────────────
def upload_foto_facebook(img_bytes: bytes) -> str | None:
    """Faz upload da imagem (sem publicar) e retorna o photo_id."""
    session = make_session()
    url = f"{FB_GRAPH}/{FB_PAGE_ID}/photos"
    files = {"source": ("news.jpg", img_bytes, "image/jpeg")}
    data = {
        "access_token": FB_TOKEN,
        "published": "false",  # upload sem publicar (anexa ao post depois)
    }
    r = session.post(url, files=files, data=data, timeout=60)
    resp = r.json()
    if "id" in resp:
        log.info(f"Foto enviada: {resp['id']}")
        return resp["id"]
    log.error(f"Erro no upload da foto: {resp}")
    return None


def publicar_post_facebook(titulo_cortado: str, photo_id: str) -> str | None:
    """Publica post com a foto na página do Facebook."""
    session = make_session()
    url = f"{FB_GRAPH}/{FB_PAGE_ID}/feed"
    data = {
        "message": f"🔥 {titulo_cortado}",
        "attached_media[0]": json.dumps({"media_fbid": photo_id}),
        "access_token": FB_TOKEN,
    }
    r = session.post(url, data=data, timeout=30)
    resp = r.json()
    if "id" in resp:
        log.info(f"Post publicado: {resp['id']}")
        return resp["id"]
    log.error(f"Erro ao publicar post: {resp}")
    return None


def comentar_link(post_id: str, link: str):
    """Adiciona o link da notícia como primeiro comentário."""
    session = make_session()
    url = f"{FB_GRAPH}/{post_id}/comments"
    data = {
        "message": f"🔗 Leia a notícia completa: {link}",
        "access_token": FB_TOKEN,
    }
    r = session.post(url, data=data, timeout=20)
    resp = r.json()
    if "id" in resp:
        log.info("Comentário com link adicionado.")
    else:
        log.warning(f"Resposta do comentário: {resp}")


# ──────────────────────────────────────────────
# FLUXO PRINCIPAL
# ──────────────────────────────────────────────
def main():
    log.info("=" * 50)
    log.info("  SharesForYou → Facebook Bot v2  ")
    log.info("=" * 50)

    posted = load_posted()
    noticias = get_noticias_playwright()

    if not noticias:
        log.error("Nenhuma notícia encontrada. Verifique as credenciais do SharesForYou.")
        return

    publicados = 0
    for noticia in noticias:
        if noticia["id"] in posted:
            log.info(f"[SKIP já postada] {noticia['title'][:50]}")
            continue

        log.info(f"\n[PROCESSANDO] {noticia['title'][:60]}")

        # 1. Buscar imagem
        img_bytes = get_image_from_article(noticia)
        if not img_bytes:
            log.warning("[SKIP] Sem imagem válida. Pulando.")
            continue

        # 2. Gerar gancho com IA
        gancho = gerar_gancho(noticia["title"])
        log.info(f"[GANCHO] {gancho}")

        # 3. Modificar imagem
        palette = palette_for(noticia["id"])
        try:
            img_modificada = adicionar_texto_imagem(img_bytes, gancho, palette)
        except Exception as e:
            log.error(f"Erro no processamento de imagem: {e}")
            continue

        # 4. Upload imagem no Facebook
        photo_id = upload_foto_facebook(img_modificada)
        if not photo_id:
            continue

        # 5. Publicar post
        titulo_cortado = truncate_title(noticia["title"])
        post_id = publicar_post_facebook(titulo_cortado, photo_id)
        if not post_id:
            continue

        # 6. Comentar com link
        time.sleep(2)
        comentar_link(post_id, noticia["share_link"])

        # 7. Marcar como postada (anti-duplicata)
        posted.add(noticia["id"])
        save_posted(posted)
        publicados += 1

        # Pausa entre posts
        time.sleep(5)

        # 1 notícia por execução (roda a cada hora)
        break

    if publicados == 0:
        log.info("Nenhuma notícia nova para postar neste ciclo.")
    else:
        log.info(f"CONCLUÍDO: {publicados} notícia(s) publicada(s).")


if __name__ == "__main__":
    main()
