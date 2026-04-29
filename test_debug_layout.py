import bot
from PIL import Image, ImageDraw, ImageFont

img = Image.new("RGBA", (2160, 2160), (0,0,0,0))
draw_core = ImageDraw.Draw(img)
bw, bh = 2160, 2160
sf = 2

# Simulando a parte relevante do adicionar_texto_premium
font_path = bot.baixar_fonte()
print(f"Font Path: {font_path}")

reactions = [("1f631", "QUE ABSURDO!"), ("1f4b8", "SÓ PREJUÍZO!"), ("1f693", "PEGA ELES!")]

r_emoji_size = int(bh * 0.05) 
f_react_size = int(bh * 0.032)
f_react = ImageFont.truetype(font_path, f_react_size) if font_path else ImageFont.load_default()

print(f"Font size: {f_react_size}")

gap = int(70 * sf)
sp = int(12 * sf)
items = []
tot_w = 0

for (r_hex, r_text) in reactions:
    r_text = r_text.strip().upper()
    lbb = draw_core.textbbox((0, 0), r_text, font=f_react)
    lw_r = lbb[2] - lbb[0]
    print(f"Reaction '{r_text}': lbb={lbb}, lw_r={lw_r}")
    item_w = r_emoji_size + sp + lw_r
    items.append({"hex": r_hex, "text": r_text, "w": item_w})
    tot_w += item_w

tot_w += gap * (len(reactions) - 1)
print(f"Total Width: {tot_w}")

rx = (bw - tot_w) // 2
print(f"Start rx: {rx}")

render_y = 1900

for item in items:
    tx_p = rx + r_emoji_size + sp
    ty_p = render_y + (r_emoji_size // 2)
    print(f"Drawing emoji at: {rx}, {render_y}")
    print(f"Drawing text '{item['text']}' at: {tx_p}, {ty_p}")
    rx += item["w"] + gap

footer_txt = 'Clique em "...mais" para ver na íntegra'
f_footer_size = int(bh * 0.035)
f_footer = ImageFont.truetype(font_path, f_footer_size) if font_path else ImageFont.load_default()
f_bbox = draw_core.textbbox((0, 0), footer_txt, font=f_footer)
fw = f_bbox[2] - f_bbox[0]

fx = (bw - fw) // 2
fy = bh - int(25 * sf) 
print(f"Drawing footer at: {fx}, {fy}")
