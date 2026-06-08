# -*- coding: utf-8 -*-
from datetime import datetime
from .whatsapp import send_buttons, send_message

ISSUE_MAP = {
    "product":      ("Probleme Produit",                  "Product"),
    "relation":     ("Probleme Relation / micro-distrib", "Relationship"),
    "income":       ("Probleme Revenu / paiement",        "Income"),
    "motivation":   ("Motivation / formation",            "Motivation"),
    "equipment":    ("Probleme Equipement",               "Equipment"),
    "prix":         ("Confirmation prix du jour",         ""),
    "support":      ("Demande support direct",            ""),
    "aucun":        ("Aucun probleme",                    ""),
}

VENDOR_MEMORY = {}  # { phone: vendor_id }
SESSIONS = {}

MOTS_INVALIDES = [
    "oui", "non", "ok", "yes", "no", "menu", "bonjour", "bonsoir",
    "salut", "allo", "allô", "peut-etre", "peut être", "1", "2", "3",
    "consent_oui", "consent_non", "present_oui", "present_non", "present_peut"
]


def get_session(phone):
    if phone not in SESSIONS:
        SESSIONS[phone] = {"step": "consent", "data": {}}
    return SESSIONS[phone]


def reset_session(phone):
    SESSIONS[phone] = {"step": "consent", "data": {}}


def handle_message(phone, body):
    body = body.strip()
    session = get_session(phone)
    step = session["step"]
    data = session["data"]

    if body.upper() == "MENU":
        reset_session(phone)
        get_session(phone)["step"] = "issue1"
        _send_issue_part1(phone)
        return None, None

    # ── ETAPE 0 : Consentement ────────────────────────────────────────────────
    if step == "consent":
        session["step"] = "id"
        send_buttons(phone,
            "Bienvenue chez *Company Vendor Support* !\n\n"
            "Acceptez-vous de recevoir nos messages WhatsApp sur les produits, "
            "prix, formation et operations vendeurs ?",
            [
                {"id": "consent_oui", "title": "Oui j'accepte"},
                {"id": "consent_non", "title": "Non merci"},
            ]
        )
        return None, None

    # ── ETAPE 1 : Vendor ID ───────────────────────────────────────────────────
    if step == "id":
        if body == "consent_non":
            reset_session(phone)
            send_message(phone, "Pas de probleme. Envoyez *MENU* a tout moment.")
            return None, None

        data["consent"] = "Oui"

        # Vendor deja connu → skip ID, on l'enregistre directement
        if phone in VENDOR_MEMORY:
            data["vendor_id"] = VENDOR_MEMORY[phone]
            session["step"] = "attendance"
            send_buttons(phone,
                "Bonjour ! Content de vous revoir !\n\n"
                "Etes-vous en train de vendre *aujourd'hui* ?",
                [
                    {"id": "present_oui",  "title": "Oui je vends"},
                    {"id": "present_peut", "title": "Peut-etre"},
                    {"id": "present_non",  "title": "Non pas aujourd'hui"},
                ]
            )
            return None, None

        session["step"] = "attendance"
        send_message(phone,
            "Merci !\n\n"
            "Veuillez entrer votre *ID Vendeur*.\n"
            "_(exemple : V-0042)_"
        )
        return None, None

    # ── ETAPE 2 : Presence ────────────────────────────────────────────────────
    if step == "attendance":
        # Enregistrement ID si pas encore fait
        if "vendor_id" not in data:
            if body.lower() in MOTS_INVALIDES or len(body) < 2:
                send_message(phone,
                    "Veuillez entrer votre *ID Vendeur* valide.\n"
                    "_(exemple : V-0042 ou 90123456)_"
                )
                return None, None
            data["vendor_id"] = body
            VENDOR_MEMORY[phone] = body
            send_buttons(phone,
                "ID enregistre : *{}*\n\n"
                "Etes-vous en train de vendre *aujourd'hui* ?".format(body),
                [
                    {"id": "present_oui",  "title": "Oui je vends"},
                    {"id": "present_peut", "title": "Peut-etre"},
                    {"id": "present_non",  "title": "Non pas aujourd'hui"},
                ]
            )
            return None, None

        # Reponse presence
        if body == "present_oui":
            data["attendance"] = "Oui"
        elif body == "present_peut":
            data["attendance"] = "Peut-etre"
        elif body == "present_non":
            data["attendance"] = "Non"
        else:
            send_buttons(phone,
                "Etes-vous en train de vendre *aujourd'hui* ?",
                [
                    {"id": "present_oui",  "title": "Oui je vends"},
                    {"id": "present_peut", "title": "Peut-etre"},
                    {"id": "present_non",  "title": "Non pas aujourd'hui"},
                ]
            )
            return None, None

        session["step"] = "issue1"
        _send_issue_part1(phone)
        return None, None

    # ── ETAPE 3a : Probleme PRIME — partie 1 (3 choix) ───────────────────────
    if step == "issue1":
        if body in ["product", "relation", "income"]:
            return _handle_issue(phone, body, session, data)
        elif body == "suite":
            session["step"] = "issue2"
            _send_issue_part2(phone)
            return None, None
        else:
            _send_issue_part1(phone)
            return None, None

    # ── ETAPE 3b : Probleme PRIME — partie 2 ────────────────────────────────
    if step == "issue2":
        if body in ["motivation", "equipment", "income"]:
            return _handle_issue(phone, body, session, data)
        elif body == "suite2":
            session["step"] = "issue3"
            _send_issue_part3(phone)
            return None, None
        else:
            _send_issue_part2(phone)
            return None, None

    # ── ETAPE 3c : Probleme PRIME — partie 3 ────────────────────────────────
    if step == "issue3":
        if body in ["prix", "support", "aucun"]:
            return _handle_issue(phone, body, session, data)
        else:
            _send_issue_part3(phone)
            return None, None

    # ── ETAPE 4 : Commentaire ─────────────────────────────────────────────────
    if step == "comment":
        if body == "comment_non":
            row = _build_row(phone, data, "")
            reset_session(phone)
            send_message(phone,
                "Merci, votre probleme a bien ete recu !\n\n"
                "Notre equipe fera un suivi via votre micro-distributeur "
                "ou superviseur commercial.\n\n"
                "*A demain !*"
            )
            return None, row
        elif body == "comment_oui":
            session["step"] = "comment_text"
            send_message(phone, "Decrivez brievement votre probleme :")
            return None, None
        else:
            row = _build_row(phone, data, body)
            reset_session(phone)
            send_message(phone,
                "Merci, votre probleme a bien ete recu !\n\n"
                "Notre equipe fera un suivi via votre micro-distributeur "
                "ou superviseur commercial.\n\n"
                "*A demain !*"
            )
            return None, row

    # ── ETAPE 4b : Texte commentaire ─────────────────────────────────────────
    if step == "comment_text":
        row = _build_row(phone, data, body)
        reset_session(phone)
        send_message(phone,
            "Merci, votre probleme a bien ete recu !\n\n"
            "Notre equipe fera un suivi via votre micro-distributeur "
            "ou superviseur commercial.\n\n"
            "*A demain !*"
        )
        return None, row

    reset_session(phone)
    send_message(phone, "Envoyez *MENU* pour acceder au support.")
    return None, None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _handle_issue(phone, body, session, data):
    categorie, prime = ISSUE_MAP[body]
    data["categorie"] = categorie
    data["prime"] = prime

    if body == "aucun":
        row = _build_row(phone, data, "")
        reset_session(phone)
        send_message(phone,
            "Parfait, bonne journee de vente !\n\n"
            "Votre presence a bien ete enregistree.\n\n"
            "*A demain !*"
        )
        return None, row

    if body == "prix":
        row = _build_row(phone, data, "Demande prix du jour")
        reset_session(phone)
        send_message(phone,
            "Votre demande de prix a ete transmise.\n\n"
            "Notre equipe vous repond rapidement.\n\n"
            "*A demain !*"
        )
        return None, row

    if body == "support":
        row = _build_row(phone, data, "Demande support direct")
        reset_session(phone)
        send_message(phone,
            "Un agent vous contactera tres prochainement.\n\n"
            "*A demain !*"
        )
        return None, row

    session["step"] = "comment"
    send_buttons(phone,
        "Vous avez signale : *{}*\n\n"
        "Voulez-vous ajouter un commentaire ?".format(categorie),
        [
            {"id": "comment_oui", "title": "Oui je decris"},
            {"id": "comment_non", "title": "Non continuer"},
        ]
    )
    return None, None


def _send_issue_part1(phone):
    send_buttons(phone,
        "Avez-vous un probleme aujourd'hui ? *(1/2)*",
        [
            {"id": "product",  "title": "Probleme Produit"},
            {"id": "relation", "title": "Probleme Relation"},
            {"id": "suite",    "title": "Voir plus..."},
        ]
    )


def _send_issue_part2(phone):
    send_buttons(phone,
        "Avez-vous un probleme aujourd'hui ? *(2/3)*",
        [
            {"id": "income",     "title": "Revenu / paiement"},
            {"id": "motivation", "title": "Motivation / formation"},
            {"id": "suite2",     "title": "Voir plus..."},
        ]
    )


def _send_issue_part3(phone):
    send_buttons(phone,
        "Autres options :",
        [
            {"id": "prix",    "title": "Prix du jour"},
            {"id": "support", "title": "Parler au support"},
            {"id": "aucun",   "title": "Aucun probleme"},
        ]
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

# NOTE pour main.py :
# Apres issue2, si l'utilisateur clique "Voir plus...", envoyer _send_issue_part3
# Ajouter dans le flow issue2 :
# elif body == "suite2":
#     _send_issue_part3(phone)
