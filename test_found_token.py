import requests

TOKEN = "EAASPZAaNHHcYBRM0ZBS9XZBgmiJT5fjQ66nTI9kScsnKq73IZAGdnUmZBZBSrQusmjR70dn2ZAwjVWnt024JyDRL4gR8pVoYDPdMJz2qKoZBp8arZArGybCD2EeZCZBF1B9ZARuJ828v6uD3IoiUJxuZC8HModx3cJnTZCLCzTPzuYXoQdtqi4Cy9IO6SQotKX9PsXSZBZBB8ZALQZBqTkblboRI4B4svqueG4usR6vgCvIVHFmSoZD"
PAGE_ID = "1021302557732355"

url = f"https://graph.facebook.com/v22.0/{PAGE_ID}?fields=name&access_token={TOKEN}"
r = requests.get(url)
print(f"Status: {r.status_code}")
print(f"Response: {r.text}")
