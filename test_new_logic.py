import bot
import os
from dotenv import load_dotenv

load_dotenv()

def test_visuals():
    title = "URGENTE: Nova variante descoberta em SP"
    print(f"Testando com título: {title}")
    
    # Simula resposta do Gemini
    estetica = bot.gerar_gancho(title)
    print(f"Estética gerada: {estetica}")
    
    # Simula imagem em branco ou usa uma local
    img_path = "absolute_final_0.jpg"
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            content = f.read()
    else:
        print("Imagem local não encontrada, tentando placeholder...")
        import requests
        content = requests.get("https://via.placeholder.com/800", verify=False).content
    
    img_b = bot.adicionar_texto_premium(content, estetica)
    
    with open("test_output_premium.jpg", "wb") as f:
        f.write(img_b)
    print("Imagem de teste salva em test_output_premium.jpg")

if __name__ == "__main__":
    test_visuals()
