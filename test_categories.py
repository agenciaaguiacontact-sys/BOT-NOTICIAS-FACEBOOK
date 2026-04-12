import bot
import os
from dotenv import load_dotenv

load_dotenv()

def test_themes():
    themes = [
        {"title": "Homem morto em tiroteio no centro", "expected": "CRIME"},
        {"title": "Nova lei de impostos aprovada pelo senado", "expected": "POLITICA"},
        {"title": "Flamengo vence clássico e assume liderança", "expected": "ESPORTE"},
        {"title": "Cantor famoso é visto com nova namorada em Paris", "expected": "FOFOCA"},
        {"title": "ALERTA: Ciclone se aproxima da costa sul", "expected": "URGENTE"}
    ]
    
    img_path = "absolute_final_0.jpg"
    if not os.path.exists(img_path):
        print("Erro: absolute_final_0.jpg não encontrada para testes.")
        return

    with open(img_path, "rb") as f:
        content = f.read()

    for i, t in enumerate(themes):
        print(f"\n--- Teste {i+1}: {t['title']} ---")
        estetica = bot.gerar_gancho(t["title"])
        print(f"Estética sugerida: {estetica}")
        
        # O teste também valida se a censura funcionou visualmente nos logs
        # Se contiver 'MORTE' ou 'MORTO' sem censura, o bot falhou na instrução
        
        img_b = bot.adicionar_texto_premium(content, estetica)
        filename = f"test_theme_{i}_{estetica.get('tag', 'unknown').replace(' ', '_')}.jpg"
        with open(filename, "wb") as f:
            f.write(img_b)
        print(f"Salvo em: {filename}")

if __name__ == "__main__":
    test_themes()
