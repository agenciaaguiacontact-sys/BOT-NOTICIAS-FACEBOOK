import os
import json
import logging
from playwright.sync_api import sync_playwright
import hashlib

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

SFY_EMAIL = "robsonvitapm67@gmail.com"
SFY_PASSWORD = "Maracana12345@"
SFY_SHARE = "https://www.sharesforyou.com/dashboard/share"
SFY_LOGIN = "https://www.sharesforyou.com/login"

def make_article_id(url):
    return hashlib.sha256(url.encode()).hexdigest()[:16]

def get_noticias():
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
            log.info("Logado. Indo para Share...")
            page.goto(SFY_SHARE)
            page.wait_for_timeout(7000)
            
            log.info("Selecionando bloco Sharesforyou...")
            try:
                page.click("button.change-order-by:has-text('Sharesforyou')", timeout=10000)
                page.wait_for_timeout(5000)
            except Exception as e:
                log.warning(f"Não foi possível clicar no botão Sharesforyou: {e}")
            
            cards = page.locator(".card").all()
            log.info(f"Encontrados {len(cards)} cards.")
            for card in cards:
                try:
                    title = card.locator("h5, p.fs-4").first.inner_text().strip()
                    link = card.locator("a:has(i.ti-eye)").first.get_attribute("href")
                    img = card.locator("img").first.get_attribute("src")
                    if link and title:
                        if link.startswith("/"): link = "https://www.sharesforyou.com" + link
                        if img and img.startswith("/"): img = "https://www.sharesforyou.com" + img
                        res.append({"id":make_article_id(link), "title":title, "link":link, "img":img})
                        log.info(f"Notícia capturada: {title}")
                except Exception as e: 
                    log.error(f"Erro no card: {e}")
                    continue
        except Exception as e: log.error(f"Erro Playwright: {e}")
        finally: browser.close()
    return res

if __name__ == "__main__":
    news = get_noticias()
    print(f"\nTotal: {len(news)}")
    if news:
        print(f"Primeira: {news[0]}")
