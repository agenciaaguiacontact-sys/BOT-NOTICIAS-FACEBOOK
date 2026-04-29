import bot
from PIL import Image

def test():
    # Cria uma imagem de teste
    img = Image.new("RGB", (1080, 1080), color=(100, 100, 100))
    img.save("test_base.jpg")
    
    with open("test_base.jpg", "rb") as f:
        img_bytes = f.read()
        
    estetica = {
        "hook": "LIMPA NO LUXO",
        "tag": "CRIME AGORA",
        "color": (0, 0, 0, 200),
        "emoji": "1f48e", # Diamond
        "hashtags": "#noticias",
        "category": "CRIME",
        "reactions": [("1f631", "QUE ABSURDO!"), ("1f4b8", "SÓ PREJUÍZO!"), ("1f693", "PEGA ELES!")]
    }
    
    out_bytes = bot.adicionar_texto_premium(img_bytes, estetica)
    
    with open("test_output.jpg", "wb") as f:
        f.write(out_bytes)
        
    print("Imagem gerada com sucesso.")

if __name__ == "__main__":
    test()
