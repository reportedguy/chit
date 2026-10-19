"""Regenerate the README logos and the GitHub social preview card in docs/images/.
Usage: python scripts/make_brand_images.py"""

import os

from PIL import Image, ImageDraw, ImageFont

from chit.icon import BLUE, app_icon

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "images")
os.makedirs(OUT, exist_ok=True)

for theme in ("light", "dark"):
    app_icon(256, theme).save(os.path.join(OUT, f"logo-{theme}.png"))

# 1280x640 social preview (GitHub recommends this size).
W, H = 1280, 640
card = Image.new("RGBA", (W, H), (12, 15, 20, 255))
draw = ImageDraw.Draw(card)
logo = app_icon(300, "dark")
card.alpha_composite(logo, (110, (H - 300) // 2))
title = ImageFont.truetype("segoeuib.ttf", 120)
body = ImageFont.truetype("segoeui.ttf", 40)
small = ImageFont.truetype("segoeui.ttf", 30)
x = 470
draw.text((x, 150), "Chit", font=title, fill=(255, 255, 255))
draw.text((x, 305), "Hold Caps Lock. Talk. Clean text appears.", font=body, fill=(230, 232, 236))
draw.text((x, 365), "Free, open-source voice dictation that runs", font=body, fill=(170, 176, 186))
draw.text((x, 415), "entirely on your PC.", font=body, fill=(170, 176, 186))
draw.rounded_rectangle((x, 495, x + 520, 545), radius=25, outline=BLUE, width=3)
draw.text((x + 260, 520), "Windows  ·  Whisper  ·  100% local", font=small, fill=(210, 222, 255), anchor="mm")
card.convert("RGB").save(os.path.join(OUT, "social-preview.png"), optimize=True)
print("saved to", OUT)
