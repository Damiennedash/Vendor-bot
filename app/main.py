"""
Vendor Daily Check-In — WhatsApp Webhook
Stack : Flask + WhatsApp Cloud API + Google Sheets
"""

import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from .conversation import handle_message
from .sheets import append_row

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "mon_token_secret")


@app.route("/")
def index():
    return (
        "<h1>Vendor Bot</h1>"
        "<p>Available endpoints:</p>"
        "<ul><li><a href='/webhook'>/webhook</a> (GET/POST)</li></ul>",
        200,
    )


@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Webhook vérifié avec succès ✅")
        return challenge, 200
    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)
    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]["value"]

        # Ignorer les notifications de statut (delivered, read…)
        if "messages" not in changes:
            return jsonify({"status": "ok"}), 200

        message = changes["messages"][0]
        phone = message["from"]
        msg_type = message.get("type")

        # Texte libre ou réponses interactives
        if msg_type == "text":
            body = message["text"]["body"].strip()
        elif msg_type == "interactive":
            itype = message["interactive"].get("type")
            if itype == "button_reply":
                body = message["interactive"]["button_reply"].get("id", "").strip()
            elif itype == "list_reply":
                body = message["interactive"]["list_reply"].get("id", "").strip()
            else:
                return jsonify({"status": "ok"}), 200
        else:
            return jsonify({"status": "ok"}), 200

        logger.info("Message reçu de %s: %s", phone, body)

        # Traiter la conversation
        reply, completed_row = handle_message(phone, body)

        # Envoyer la réponse si nécessaire
        if reply:
            from .whatsapp import send_message
            send_message(phone, reply)

        # Écrire dans Google Sheets si flow terminé
        if completed_row:
            append_row(completed_row)
            logger.info("Ligne enregistrée dans Sheets pour %s", phone)

    except Exception as e:
        logger.error("Erreur webhook: %s", e, exc_info=True)

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
