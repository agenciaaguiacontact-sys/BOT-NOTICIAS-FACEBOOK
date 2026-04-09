import requests

url = "https://www.sharesforyou.com/storage/article/69d6ba5855e976.webp" # Exemplo baseado no log
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.sharesforyou.com/dashboard/share"
}

r = requests.get(url, headers=headers)
print(f"Status: {r.status_code}")
if r.status_code == 200:
    print("Sucesso!")
else:
    print(f"Erro: {r.text[:100]}")
