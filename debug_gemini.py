import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

def test_raw_gemini():
    title = "Homem morto em tiroteio no centro"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    prompt = (
        f"Analise a notícia: \"{title}\".\n"
        f"Atue como um editor de notícias sensacionalista de alto impacto.\n"
        f"Retorne APENAS uma linha no formato: HOOK | CATEGORY | EMOJI\n"
        f"- HOOK: Título EXTREMAMENTE CURTO (MÁXIMO 3 PALAVRAS) em MAIÚSCULAS.\n"
        f"  IMPORTANTE: CAMUFLE palavras sensíveis trocando letras por números/símbolos.\n"
        f"  Ex: MORTE -> M0RT3, ESTUPRO -> 3STUPR0, SANGUE -> S@NGU3, MATOU -> M@T0U, TIRO -> T1R0.\n"
        f"- CATEGORY: Escolha exatamente uma: URGENTE, POLITICA, ESPORTE, FOFOCA, CRIME.\n"
        f"- EMOJI: UM único emoji que combine com o tema.\n"
    )
    payload = {"contents":[{"parts":[{"text":prompt}]}]}
    r = requests.post(url, json=payload, timeout=15)
    print("STATUS:", r.status_code)
    print("RAW RESPONSE:", r.text)

if __name__ == "__main__":
    test_raw_gemini()
