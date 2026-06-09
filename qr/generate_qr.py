# -*- coding: utf-8 -*-
"""
Generateur de 20 QR codes vendors — 2 par page, PDF imprimable
Chaque QR code contient l'ID du vendor dans le message WhatsApp
"""
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from PIL import Image
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Image as RLImage
import os
import argparse
# ── Configuration ─────────────────────────────────────────────────────────────
WA_PHONE = "22899432898"  # Ton numero WhatsApp Business sans +
# ── Liste fictive des 20 vendors ──────────────────────────────────────────────
VENDORS = [
   {"id": "V-001", "nom": "Kofi Mensah",      "zone": "Lome Centre"},
   {"id": "V-002", "nom": "Ama Koffi",        "zone": "Baguida"},
   {"id": "V-003", "nom": "Kwame Agbeko",     "zone": "Kara"},
   {"id": "V-004", "nom": "Efua Tsevi",       "zone": "Aneho"},
   {"id": "V-005", "nom": "Yao Dossou",       "zone": "Kara"},
   {"id": "V-006", "nom": "Abla Gbekor",      "zone": "Baguida"},
   {"id": "V-007", "nom": "Komla Foli",       "zone": "Baguida"},
   {"id": "V-008", "nom": "Akosua Degli",     "zone": "Lome Centre"},
   {"id": "V-009", "nom": "Mawuli Atsu",      "zone": "Kara"},
   {"id": "V-010", "nom": "Sena Gakpo",       "zone": "Baguida"},
   {"id": "V-011", "nom": "Kossi Amavi",      "zone": "Lome Centre"},
   {"id": "V-012", "nom": "Yawa Abledu",      "zone": "Kara"},
   {"id": "V-013", "nom": "Edem Kuevi",       "zone": "Aneho"},
   {"id": "V-014", "nom": "Dzifa Akoto",      "zone": "Lome Centre"},
   {"id": "V-015", "nom": "Kosi Segla",       "zone": "Kpalimé"},
   {"id": "V-016", "nom": "Fiavi Amewu",      "zone": "Kara"},
   {"id": "V-017", "nom": "Togbe Lawson",     "zone": "Lome Centre"},
   {"id": "V-018", "nom": "Akpene Kpodo",     "zone": "Baguida"},
   {"id": "V-019", "nom": "Selom Agbodji",    "zone": "Aneho"},
   {"id": "V-020", "nom": "Mawuena Tetteh",   "zone": "Baguida"},
]

def make_qr_image(vendor_id, nom):
   """Genere un QR code avec l'ID et le NOM vendor integres dans le message."""
   nom_encode = nom.replace(" ", "%20")
   msg = "Bonjour, je souhaite enregistrer ma presence du jour. ID:{} NOM:{}".format(vendor_id, nom)
   url = "https://wa.me/{}?text={}".format(
       WA_PHONE,
       msg.replace(" ", "%20").replace(":", "%3A")
   )
   qr = qrcode.QRCode(
       version=3,
       error_correction=qrcode.constants.ERROR_CORRECT_H,
       box_size=10,
       border=2,
   )
   qr.add_data(url)
   qr.make(fit=True)
   img = qr.make_image(
       image_factory=StyledPilImage,
       module_drawer=RoundedModuleDrawer()
   ).convert("RGB")
   buf = io.BytesIO()
   img.save(buf, format="PNG")
   buf.seek(0)
   return buf

def build_pdf(output_path):
   doc = SimpleDocTemplate(
       output_path,
       pagesize=A4,
       rightMargin=1.5*cm,
       leftMargin=1.5*cm,
       topMargin=1.5*cm,
       bottomMargin=1.5*cm,
   )
   styles = getSampleStyleSheet()
   title_style = ParagraphStyle(
       "title", fontSize=11, fontName="Helvetica-Bold",
       textColor=colors.HexColor("#075E54"), alignment=1, spaceAfter=4
   )
   sub_style = ParagraphStyle(
       "sub", fontSize=9, fontName="Helvetica",
       textColor=colors.HexColor("#333333"), alignment=1, spaceAfter=2
   )
   zone_style = ParagraphStyle(
       "zone", fontSize=8, fontName="Helvetica",
       textColor=colors.HexColor("#777777"), alignment=1
   )
   header_style = ParagraphStyle(
       "header", fontSize=14, fontName="Helvetica-Bold",
       textColor=colors.HexColor("#075E54"), alignment=1, spaceAfter=8
   )
   story = []
   # Traiter par paires (2 vendors par page)
   for i in range(0, len(VENDORS), 2):
       pair = VENDORS[i:i+2]
       # En-tete page
       story.append(Paragraph("Company Vendor Support — QR Check-In Quotidien", header_style))
       story.append(Spacer(1, 0.3*cm))
       # Construire les 2 cellules
       cells = []
       for v in pair:
           qr_buf = make_qr_image(v["id"], v["nom"])
           qr_img = RLImage(qr_buf, width=7*cm, height=7*cm)
           cell_content = [
               qr_img,
               Spacer(1, 0.2*cm),
               Paragraph(v["id"], title_style),
               Paragraph(v["nom"], sub_style),
               Paragraph(v["zone"], zone_style),
               Spacer(1, 0.3*cm),
               Paragraph("Scannez pour declarer votre presence", zone_style),
           ]
           cells.append(cell_content)
       # Si nombre impair, ajouter cellule vide
       if len(pair) == 1:
           cells.append([Spacer(1, 1)])
       table = Table(
           [cells],
           colWidths=[9*cm, 9*cm],
           rowHeights=[11*cm],
       )
       table.setStyle(TableStyle([
           ("ALIGN",       (0,0), (-1,-1), "CENTER"),
           ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
           ("BOX",         (0,0), (0,0), 1.5, colors.HexColor("#075E54")),
           ("BOX",         (1,0), (1,0), 1.5, colors.HexColor("#075E54")),
           ("LEFTPADDING", (0,0), (-1,-1), 12),
           ("RIGHTPADDING",(0,0), (-1,-1), 12),
           ("TOPPADDING",  (0,0), (-1,-1), 12),
           ("BOTTOMPADDING",(0,0),(-1,-1), 12),
           ("ROUNDEDCORNERS", [8]),
       ]))
       story.append(table)
       # Saut de page sauf derniere
       if i + 2 < len(VENDORS):
           story.append(PageBreak())
   doc.build(story)
   print("PDF genere : {}".format(output_path))
def save_pngs(output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    for v in VENDORS:
        buf = make_qr_image(v['id'], v['nom'])
        path = os.path.join(output_dir, f"{v['id']}.png")
        with open(path, 'wb') as f:
            f.write(buf.getbuffer())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Génère PDF et PNG de QR codes vendors')
    parser.add_argument('--phone', help='Numéro WhatsApp sans +', default=WA_PHONE)
    parser.add_argument('--output', help='Chemin du PDF de sortie', default='qr/vendors_qr_codes.pdf')
    args = parser.parse_args()

    # override phone if provided
    WA_PHONE = args.phone

    # generate individual PNGs
    png_dir = os.path.join(os.path.dirname(__file__), 'output')
    save_pngs(png_dir)

    # ensure output directory exists for PDF
    out_dir = os.path.dirname(args.output)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    build_pdf(args.output)