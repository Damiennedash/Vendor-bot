"""
Génère le QR code final pointant vers ton numéro WhatsApp Business réel.
Lance ce script UNE FOIS après avoir configuré ton numéro.

Usage:
    python generate_qr.py --phone 22896015921 --output qr_vendor.png
"""

import argparse, qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from PIL import Image, ImageDraw, ImageFont

def generate(phone: str, output: str = "vendor_qr.png"):
    message = "Bonjour, je souhaite enregistrer ma présence du jour."
    url     = f"https://wa.me/{phone}?text={message.replace(' ', '%20')}"
    print(f"✅ URL encodée : {url}")

    qr = qrcode.QRCode(
        version=3,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=14,
        border=3,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer()
    ).convert("RGBA")

    W, H = img.size
    canvas = Image.new("RGBA", (W, H + 90), (255, 255, 255, 255))
    canvas.paste(img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, H, W, H + 90], fill=(7, 94, 84, 255))  # vert WhatsApp

    try:
        f_bold  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 19)
        f_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except:
        f_bold = f_small = ImageFont.load_default()

    draw.text((W//2, H + 24), "Scannez pour déclarer votre présence",
              fill="white", font=f_bold, anchor="mm")
    draw.text((W//2, H + 54), "Vendor Daily Check-In • WhatsApp",
              fill=(178, 223, 219), font=f_small, anchor="mm")
    draw.text((W//2, H + 74), f"wa.me/{phone}",
              fill=(178, 223, 219), font=f_small, anchor="mm")

    canvas.save(output)
    print(f"✅ QR code enregistré : {output}")
    print("👉 Imprimez-le et plastifiez-le chez chaque micro-distributeur.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phone",  required=True, help="22896015921")
    parser.add_argument("--output", default="vendor_qr.png")
    args = parser.parse_args()
    generate(args.phone, args.output)
