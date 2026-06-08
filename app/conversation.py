# -*- coding: utf-8 -*-
from datetime import datetime

ISSUE_MAP = {
    "1": ("Probleme Produit",                  "Product"),
    "2": ("Probleme Relation / micro-distrib", "Relationship"),
    "3": ("Probleme Revenu / paiement",        "Income"),
    "4": ("Motivation / formation",            "Motivation"),
    "5": ("Probleme Equipement",               "Equipment"),
    "6": ("Confirmation prix du jour",         ""),
    "7": ("Demande support direct",            ""),
    "8": ("Aucun probleme",                    ""),
}

# Memoire permanente : { phone: vendor_id }
VENDOR_MEMORY = {}
SESSIONS = {}

MOTS_INVALIDES = [
    "oui", "non", "ok", "yes", "no", "menu", "bonjour", "bonsoir",
    "salut", "allo", "peut-etre", "1", "2", "3", "4", "5", "6", "7", "8",
    "bonjour, je souhaite enregistrer ma presence du jour.",
    "bonjour, je souhaite enregistrer ma présence du jour.",
]


def get_session(phone):
    if phone not in SESSIONS:
        SESSIONS[phone] = {"step": "consent", "data": {}}
    return SESSIONS[phone]


def reset_session(phone):
    SESSIONS[phone] = {"step": "consent", "data": {}}


def handle_message(phone, body):
    body_raw = body.strip()
    body = body_raw.lower().strip()
    session = get_session(phone)
    step = session["step"]
    data = session["data"]

    if body == "menu":
        reset_session(phone)
        get_session(phone)["step"] = "issue"
        return _menu_text(), None

    # Messages de declenchement QR → traiter comme consentement OUI
    TRIGGER_MSGS = [
        "bonjour, je souhaite enregistrer ma presence du jour.",
        "bonjour, je souhaite enregistrer ma présence du jour.",
        "bonjour je souhaite enregistrer ma presence du jour",
        "bonjour je souhaite enregistrer ma présence du jour",
    ]
    if body in TRIGGER_MSGS and step == "consent":
        session["step"] = "id"
        data["consent"] = "Oui"

        if phone in VENDOR_MEMORY:
            data["vendor_id"] = VENDOR_MEMORY[phone]
            session["step"] = "attendance"
            return (
                "Bonjour ! Content de vous revoir !\n\n"
                "Etes-vous en train de vendre *aujourd\'hui* ?\n\n"
                "1 - Oui, je vends\n"
                "2 - Peut-etre\n"
                "3 - Non, pas aujourd\'hui"
            ), None

        return (
            "Bienvenue chez *Company Vendor Support* !\n\n"
            "Veuillez entrer votre *ID Vendeur* pour commencer.\n"
            "_(exemple : V-0042)_"
        ), None

    # ── ETAPE 0 : Consentement ────────────────────────────────────────────────
    if step == "consent":
        session["step"] = "id"
        return (
            "Bienvenue chez *Company Vendor Support* !\n\n"
            "Pour mieux vous accompagner, nous aimerions vous envoyer "
            "des messages WhatsApp sur les produits, prix, formation "
            "et operations vendeurs.\n\n"
            "Repondez *OUI* pour accepter."
        ), None

    # ── ETAPE 1 : Vendor ID ───────────────────────────────────────────────────
    if step == "id":
        data["consent"] = "Oui"

        if phone in VENDOR_MEMORY:
            data["vendor_id"] = VENDOR_MEMORY[phone]
            session["step"] = "attendance"
            return (
                "Bonjour ! Content de vous revoir !\n\n"
                "Etes-vous en train de vendre *aujourd'hui* ?\n\n"
                "1 - Oui, je vends\n"
                "2 - Peut-etre\n"
                "3 - Non, pas aujourd'hui"
            ), None

        session["step"] = "attendance"
        return (
            "Merci !\n\n"
            "Veuillez entrer votre *ID Vendeur*.\n"
            "_(exemple : V-0042)_"
        ), None

    # ── ETAPE 2 : Presence ────────────────────────────────────────────────────
    if step == "attendance":
        if "vendor_id" not in data:
            if body in MOTS_INVALIDES or len(body_raw) < 2:
                return (
                    "Veuillez entrer votre *ID Vendeur* valide.\n"
                    "_(exemple : V-0042 ou 90123456)_"
                ), None
            data["vendor_id"] = body_raw
            VENDOR_MEMORY[phone] = body_raw
            return (
                "ID enregistre : *{}*\n\n"
                "Etes-vous en train de vendre *aujourd'hui* ?\n\n"
                "1 - Oui, je vends\n"
                "2 - Peut-etre\n"
                "3 - Non, pas aujourd'hui"
            ).format(body_raw), None

        if body in ["1", "oui"]:
            data["attendance"] = "Oui"
        elif body in ["2", "peut-etre", "peut être", "peutetre"]:
            data["attendance"] = "Peut-etre"
        elif body in ["3", "non"]:
            data["attendance"] = "Non"
        else:
            return (
                "Repondez avec le numero :\n\n"
                "1 - Oui, je vends\n"
                "2 - Peut-etre\n"
                "3 - Non, pas aujourd'hui"
            ), None

        session["step"] = "issue"
        return _menu_text(), None

    # ── ETAPE 3 : Probleme PRIME ──────────────────────────────────────────────
    if step == "issue":
        if body_raw not in ISSUE_MAP:
            return _menu_text(), None

        categorie, prime = ISSUE_MAP[body_raw]
        data["categorie"] = categorie
        data["prime"] = prime

        if body_raw == "8":
            row = _build_row(phone, data, "")
            reset_session(phone)
            return (
                "Parfait, bonne journee de vente !\n\n"
                "Votre presence a bien ete enregistree.\n\n"
                "*A demain !*"
            ), row

        if body_raw == "6":
            row = _build_row(phone, data, "Demande prix du jour")
            reset_session(phone)
            return (
                "Votre demande de prix a ete transmise.\n\n"
                "Notre equipe vous repond rapidement.\n\n"
                "*A demain !*"
            ), row

        if body_raw == "7":
            row = _build_row(phone, data, "Demande support direct")
            reset_session(phone)
            return (
                "Un agent vous contactera tres prochainement.\n\n"
                "*A demain !*"
            ), row

        session["step"] = "comment"
        return (
            "Vous avez signale : *{}*\n\n"
            "Decrivez brievement votre probleme _(optionnel)_ :\n"
            "_(Envoyez un tiret - si vous n'avez rien a ajouter)_"
        ).format(categorie), None

    # ── ETAPE 4 : Commentaire ─────────────────────────────────────────────────
    if step == "comment":
        commentaire = "" if body_raw in ["-", ".", " "] else body_raw
        row = _build_row(phone, data, commentaire)
        reset_session(phone)
        return (
            "Merci, votre probleme a bien ete recu !\n\n"
            "Notre equipe fera un suivi via votre micro-distributeur "
            "ou superviseur commercial.\n\n"
            "*A demain !*"
        ), row

    reset_session(phone)
    return "Envoyez *MENU* pour acceder au support.", None


def _menu_text():
    return (
        "Avez-vous un probleme aujourd'hui ?\n\n"
        "1 - J'ai un probleme produit\n"
        "2 - J'ai un probleme micro-distributeur / relation\n"
        "3 - J'ai une question revenu ou paiement\n"
        "4 - J'ai besoin d'une formation ou conseils de vente\n"
        "5 - J'ai un probleme d'equipement\n"
        "6 - Je veux confirmer le prix du jour\n"
        "7 - Je veux parler au support\n"
        "8 - Aucun probleme\n\n"
        "Repondez avec le *numero* correspondant."
    )


def _build_row(phone, data, commentaire):
    now = datetime.now()
    return [
        now.strftime("%d/%m/%Y"),
        now.strftime("%H:%M"),
        phone,
        data.get("vendor_id", "-"),
        data.get("attendance", "-"),
        data.get("categorie", "-"),
        data.get("prime", ""),
        commentaire,
        "WhatsApp QR",
    ]
