"""
Envoi de messages via WhatsApp Cloud API (Meta).
"""

import os, requests, logging

logger = logging.getLogger(__name__)

WA_TOKEN    = os.getenv("WHATSAPP_TOKEN")
PHONE_ID    = os.getenv("WHATSAPP_PHONE_ID")
API_VERSION = "v19.0"
API_URL     = f"https://graph.facebook.com/{API_VERSION}/{PHONE_ID}/messages"


def send_message(to: str, text: str) -> bool:
    """Envoie un message texte WhatsApp. Retourne True si succès."""
    headers = {
        "Authorization": f"Bearer {WA_TOKEN}",
        "Content-Type":  "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type":    "individual",
        "to":                to,
        "type":              "text",
        "text":              {"preview_url": False, "body": text},
    }
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        r.raise_for_status()
        logger.info(f"Message envoyé à {to} ✅")
        return True
    except requests.RequestException as e:
        logger.error(f"Échec envoi WhatsApp à {to}: {e}")
        return False
