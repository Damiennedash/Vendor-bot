"""
Conversation — machine à états avec boutons interactifs WhatsApp.
- Boutons Oui / Peut-être / Non pour la présence
- Liste interactive pour les 8 options PRIME
- Mémorisation du Vendor ID
- Message de fin "À demain !"
"""

from datetime import datetime
from .whatsapp import send_buttons, send_list, send_message

ISSUE_MAP = {
    "1": ("Problème Produit",                  "Product"),
    "2": ("Problème Relation / micro-distrib", "Relationship"),
    "3": ("Problème Revenu / paiement",        "Income"),
    "4": ("Motivation / formation",            "Motivation"),
    "5": ("Problème Équipement",               "Equipment"),
    "6": ("Confirmation prix du jour",         ""),
    "7": ("Demande support direct",            ""),
    "8": ("Aucun problème",                    ""),
}

VENDOR_MEMORY: dict = {}
SESSIONS: dict = {}

OUI_IDS   = ["present_oui", "✅ Oui, je vends"]
PEUT_IDS  = ["present_peut", "🔄 Peut-être"]
NON_IDS   = ["present_non", "❌ Non, pas aujourd'hui"]

PRESENCE_BUTTONS = [
    {"id": "present_oui",  "title": "✅ Oui, je vends"},
    {"id": "present_peut", "title": "🔄 Peut-être"},
    {"id": "present_non",  "title": "❌ Non, pas aujourd'hui"},
]

COMMENT_BUTTONS = [
    {"id": "comment_oui", "title": "✍️ Oui, je décris"},
    {"id": "comment_non", "title": "➡️ Non, continuer"},
]

CONSENT_BUTTONS = [
    {"id": "consent_oui", "title": "✅ Oui, j'accepte"},
    {"id": "consent_non", "title": "❌ Non merci"},
]


def get_session(phone):
    if phone not in SESSIONS:
        SESSIONS[phone] = {"step": "consent", "data": {}}
    return SESSIONS[phone]


def reset_session(phone):
    SESSIONS[phone] = {"step": "consent", "data": {}}


def handle_message(phone: str, body: str):
    body = body.strip()
    session = get_session(phone)
    step = session["step"]
    data = session["data"]

    # Commande MENU
    if body.upper() == "MENU":
        reset_session(phone)
        get_session(phone)["step"] = "issue"
        _send_issue_list(phone)
        return None, None

    # ── ÉTAPE 0 : Consentement ────────────────────────────────────────────────
    if step == "consent":
        session["step"] = "id"
        send_buttons(
            phone,
            "👋 Bienvenue chez *Company Vendor Support* !\n\n"
            "Pour mieux vous accompagner, nous aimerions vous envoyer des messages "
            "WhatsApp sur les produits, prix, formation et opérations vendeurs.\n\n"
            "Acceptez-vous de recevoir nos messages ?",
            CONSENT_BUTTONS
        )
        return None, None

    # ── ÉTAPE 1 : Vendor ID ───────────────────────────────────────────────────
    if step == "id":
        if body in ["consent_non", "❌ Non merci"]:
            reset_session(phone)
            send_message(phone, "Pas de problème. Envoyez *MENU* à tout moment. 👋")
            return None, None

        data["consent"] = "Oui"

        if phone in VENDOR_MEMORY:
            data["vendor_id"] = VENDOR_MEMORY[phone]
            session["step"] = "attendance"
            send_buttons(
                phone,
                f"Bonjour ! 👋 Content de vous revoir, *{VENDOR_MEMORY[phone]}* !\n\n"
                f"Êtes-vous en train de vendre *aujourd'hui* ?",
                PRESENCE_BUTTONS
            )
            return None, None

        session["step"] = "attendance"
        send_message(
            phone,
            "Merci ! 😊\n\n"
            "Veuillez entrer votre *ID Vendeur*.\n"
            "_(exemple : V-0042)_"
        )
        return None, None

    # ── ÉTAPE 2 : Présence ────────────────────────────────────────────────────
    if step == "attendance":
        if "vendor_id" not in data:
            data["vendor_id"] = body
            VENDOR_MEMORY[phone] = body
            send_buttons(
                phone,
                f"ID enregistré : *{body}* ✅\n\n"
                "Êtes-vous en train de vendre *aujourd'hui* ?",
                PRESENCE_BUTTONS
            )
            return None, None

        if body in OUI_IDS or body.upper() == "OUI":
            data["attendance"] = "Oui"
        elif body in PEUT_IDS or body.upper() == "PEUT-ÊTRE":
            data["attendance"] = "Peut-être"
        elif body in NON_IDS or body.upper() == "NON":
            data["attendance"] = "Non"
        else:
            send_buttons(phone, "Êtes-vous en train de vendre *aujourd'hui* ?", PRESENCE_BUTTONS)
            return None, None

        session["step"] = "issue"
        _send_issue_list(phone)
        return None, None

    # ── ÉTAPE 3 : Problème PRIME ──────────────────────────────────────────────
    if step == "issue":
        if body not in ISSUE_MAP:
            _send_issue_list(phone)
            return None, None

        categorie, prime = ISSUE_MAP[body]
        data["categorie"] = categorie
        data["prime"] = prime

        if body == "8":
            row = _build_row(phone, data, "")
            reset_session(phone)
            send_message(phone,
                "✅ *Parfait, bonne journée de vente !*\n\n"
                "Votre présence a bien été enregistrée. 🙏\n\n"
                "*À demain ! 👋*"
            )
            return None, row

        if body == "6":
            row = _build_row(phone, data, "Demande prix du jour")
            reset_session(phone)
            send_message(phone,
                "📋 Demande de confirmation de prix transmise.\n\n"
                "Notre équipe vous répond rapidement. 🙏\n\n"
                "*À demain ! 👋*"
            )
            return None, row

        if body == "7":
            row = _build_row(phone, data, "Demande support direct")
            reset_session(phone)
            send_message(phone,
                "📞 Un agent vous contactera très prochainement. 🙏\n\n"
                "*À demain ! 👋*"
            )
            return None, row

        session["step"] = "comment"
        send_buttons(
            phone,
            f"📝 Vous avez signalé : *{categorie}*\n\n"
            "Voulez-vous ajouter un commentaire ?",
            COMMENT_BUTTONS
        )
        return None, None

    # ── ÉTAPE 4 : Commentaire ─────────────────────────────────────────────────
    if step == "comment":
        if body in ["comment_non", "➡️ Non, continuer"]:
            row = _build_row(phone, data, "")
            reset_session(phone)
            send_message(phone,
                "✅ *Merci, votre problème a bien été reçu !*\n\n"
                "Notre équipe fera un suivi via votre micro-distributeur "
                "ou superviseur commercial. 🙏\n\n"
                "*À demain ! 👋*"
            )
            return None, row
        elif body in ["comment_oui", "✍️ Oui, je décris"]:
            session["step"] = "comment_text"
            send_message(phone, "Décrivez brièvement votre problème :")
            return None, None
        else:
            # texte libre direct
            row = _build_row(phone, data, body)
            reset_session(phone)
            send_message(phone,
                "✅ *Merci, votre problème a bien été reçu !*\n\n"
                "Notre équipe fera un suivi via votre micro-distributeur "
                "ou superviseur commercial. 🙏\n\n"
                "*À demain ! 👋*"
            )
            return None, row

    # ── ÉTAPE 4b : Texte commentaire ─────────────────────────────────────────
    if step == "comment_text":
        row = _build_row(phone, data, body)
        reset_session(phone)
        send_message(phone,
            "✅ *Merci, votre problème a bien été reçu !*\n\n"
            "Notre équipe fera un suivi via votre micro-distributeur "
            "ou superviseur commercial. 🙏\n\n"
            "*À demain ! 👋*"
        )
        return None, row

    reset_session(phone)
    send_message(phone, "Envoyez *MENU* pour accéder au support. 👋")
    return None, None


def _send_issue_list(phone: str):
    send_list(
        phone,
        body="Avez-vous un problème aujourd'hui ?\n\nChoisissez une option 👇",
        button_label="Voir les options",
        sections=[{
            "title": "Catégories PRIME",
            "rows": [
                {"id": "1", "title": "Problème Produit",        "description": "Qualité, fraîcheur, disponibilité"},
                {"id": "2", "title": "Problème Relation",       "description": "Micro-distributeur, superviseur"},
                {"id": "3", "title": "Revenu / paiement",       "description": "Commission, bonus, marge"},
                {"id": "4", "title": "Motivation / formation",  "description": "Conseils de vente, formation"},
                {"id": "5", "title": "Problème Équipement",     "description": "Glacière, tray, vélo, uniforme"},
                {"id": "6", "title": "Confirmer prix du jour",  "description": "Prix actuels des produits"},
                {"id": "7", "title": "Parler au support",       "description": "Contacter un agent directement"},
                {"id": "8", "title": "Aucun problème",          "description": "Tout va bien aujourd'hui"},
            ]
        }]
    )


def _build_row(phone: str, data: dict, commentaire: str) -> list:
    now = datetime.now()
    return [
        now.strftime("%d/%m/%Y"),
        now.strftime("%H:%M"),
        phone,
        data.get("vendor_id", "—"),
        data.get("attendance", "—"),
        data.get("categorie", "—"),
        data.get("prime", ""),
        commentaire,
        "WhatsApp QR",
    ]
