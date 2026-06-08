"""
Envoi de messages via WhatsApp Cloud API (Meta).
Supporte : texte simple, boutons (max 3), liste interactive (max 10)
"""
import os, requests, logging
logger = logging.getLogger(__name__)
WA_TOKEN    = os.getenv("WHATSAPP_TOKEN")
PHONE_ID    = os.getenv("WHATSAPP_PHONE_ID")
API_VERSION = "v19.0"
API_URL     = f"https://graph.facebook.com/{API_VERSION}/{PHONE_ID}/messages"

def _headers():
   return {
       "Authorization": f"Bearer {WA_TOKEN}",
       "Content-Type":  "application/json",
   }

def send_message(to: str, text: str) -> bool:
   """Envoie un message texte simple."""
   payload = {
       "messaging_product": "whatsapp",
       "recipient_type":    "individual",
       "to":                to,
       "type":              "text",
       "text":              {"preview_url": False, "body": text},
   }
   return _post(to, payload)

def send_buttons(to: str, body: str, buttons: list) -> bool:
   """
   Envoie un message avec boutons interactifs (max 3).
   buttons = [{"id": "oui", "title": "✅ Oui"}, ...]
   """
   payload = {
       "messaging_product": "whatsapp",
       "recipient_type":    "individual",
       "to":                to,
       "type":              "interactive",
       "interactive": {
           "type": "button",
           "body": {"text": body},
           "action": {
               "buttons": [
                   {"type": "reply", "reply": {"id": b["id"], "title": b["title"][:20]}}
                   for b in buttons[:3]
               ]
           }
       }
   }
   return _post(to, payload)

def send_list(to: str, body: str, button_label: str, sections: list) -> bool:
   """
   Envoie une liste interactive (max 10 options).
   sections = [{"title": "Catégorie", "rows": [{"id": "1", "title": "Option", "description": "..."}]}]
   """
   payload = {
       "messaging_product": "whatsapp",
       "recipient_type":    "individual",
       "to":                to,
       "type":              "interactive",
       "interactive": {
           "type": "list",
           "body": {"text": body},
           "action": {
               "button": button_label[:20],
               "sections": sections
           }
       }
   }
   return _post(to, payload)

def _post(to: str, payload: dict) -> bool:
   try:
       r = requests.post(API_URL, headers=_headers(), json=payload, timeout=10)
       r.raise_for_status()
logger.info(f"Message envoyé à {to} ✅")
       return True
   except requests.RequestException as e:
       logger.error(f"Échec envoi WhatsApp à {to}: {e}")
       return False