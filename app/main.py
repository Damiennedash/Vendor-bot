"""
Vendor Daily Check-In — WhatsApp Webhook
Stack : Flask + WhatsApp Cloud API + Google Sheets
"""

import os, json, logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from .conversation import handle_message
from .sheets import append_row

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/")
def index():
    return (
        "<h1>Vendor Bot</h1>"
        "<p>Available endpoints:</p>"
        "<ul><li><a href=\"/webhook\">/webhook</a> (GET/POST)</li></ul>",
        200,
    )

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")


# ── Vérification du webhook (Meta l'appelle 1 fois lors de la config) ─────────
@app.route("/webhook", methods=["GET"])
def verify():
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Webhook vérifié avec succès ✅")
        return challenge, 200
    return "Forbidden", 403


# ── Réception des messages WhatsApp ───────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)
    try:
        entry    = data["entry"][0]
        changes  = entry["changes"][0]["value"]

        # Ignorer les notifications de statut (delivered, read…)
        if "messages" not in changes:
            return jsonify({"status": "ok"}), 200

        message  = changes["messages"][0]
        phone    = message["from"]          # numéro du vendor
        msg_type = message.get("type")

        # Texte libre OU réponse bouton interactive
        if msg_type == "text":
            body = message["text"]["body"].strip()
        elif msg_type == "interactive":
            body = message["interactive"]["button_reply"]["title"].strip()
        else:
            return jsonify({"status": "ok"}), 200

        logger.info(f"Message reçu de {phone}: {body}")

        # Traiter la conversation et récupérer la réponse + une ligne si terminé
        reply, completed_row = handle_message(phone, body)

        # Envoyer la réponse WhatsApp
        from .whatsapp import send_message
        send_message(phone, reply)

        # Si le flow est terminé → écrire dans Google Sheets
        if completed_row:
            append_row(completed_row)
            logger.info(f"Ligne enregistrée dans Sheets pour {phone}")

    except Exception as e:
        logger.error(f"Erreur webhook: {e}", exc_info=True)

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
