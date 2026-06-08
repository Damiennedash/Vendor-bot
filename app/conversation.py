"""
Gestion de la conversation — machine à états par numéro de téléphone.
Toutes les étapes du check-in quotidien en français.
"""

from datetime import datetime

# ── Mapping choix → pilier PRIME ─────────────────────────────────────────────
ISSUE_MAP = {
    "1": ("Problème Produit",                 "Product"),
    "2": ("Problème Relation / micro-distrib","Relationship"),
    "3": ("Problème Revenu / paiement",       "Income"),
    "4": ("Motivation / formation",           "Motivation"),
    "5": ("Problème Équipement",              "Equipment"),
    "6": ("Aucun problème",                   ""),
    "0": ("Autre",                            "Other"),
}

# ── Sessions en mémoire (remplacer par Redis en production) ───────────────────
# Format : { phone: { "step": str, "data": dict } }
SESSIONS: dict = {}

# ── Étapes du flow ────────────────────────────────────────────────────────────
STEPS = ["consent", "id", "attendance", "issue", "comment", "done"]


def get_session(phone: str) -> dict:
    if phone not in SESSIONS:
        SESSIONS[phone] = {"step": "consent", "data": {}}
    return SESSIONS[phone]


def reset_session(phone: str):
    SESSIONS[phone] = {"step": "consent", "data": {}}


def handle_message(phone: str, body: str) -> tuple[str, list | None]:
    """
    Retourne (texte_de_réponse, ligne_sheets_ou_None).
    ligne_sheets = liste de valeurs à écrire quand le flow est complet.
    """
    body = body.strip()
    session = get_session(phone)
    step    = session["step"]
    data    = session["data"]

    # ── ÉTAPE 0 : Consentement ────────────────────────────────────────────────
    if step == "consent":
        msg = (
            "👋 Bienvenue chez *Company Vendor Support* !\n\n"
            "Pour mieux vous accompagner, nous aimerions vous envoyer des messages "
            "WhatsApp sur les produits, prix, formation et opérations vendeurs.\n\n"
            "Répondez *OUI* pour accepter ou *NON* pour refuser."
        )
        session["step"] = "id"
        return msg, None

    # ── ÉTAPE 1 : ID Vendor ───────────────────────────────────────────────────
    if step == "id":
        if body.upper() == "NON":
            reset_session(phone)
            return "Pas de problème. Vous pouvez envoyer *MENU* à tout moment pour accéder au support.", None

        data["consent"] = "Oui" if body.upper() == "OUI" else "Oui (implicite)"
        session["step"] = "attendance"
        return (
            "Merci ! 😊\n\n"
            "Veuillez entrer votre *ID Vendeur* ou votre *numéro de téléphone*.\n"
            "_(exemple : V-0042 ou 90123456)_"
        ), None

    # ── ÉTAPE 2 : Présence ────────────────────────────────────────────────────
    if step == "attendance":
        data["vendor_id"] = body
        session["step"]   = "issue"
        return (
            f"Bonjour ! 👋\n\n"
            f"Êtes-vous en train de vendre *aujourd'hui* ?\n\n"
            f"Répondez *1* pour Oui ou *2* pour Non."
        ), None

    # ── ÉTAPE 3 : Problème (PRIME) ────────────────────────────────────────────
    if step == "issue":
        if body == "1":
            data["attendance"] = "Oui"
        elif body == "2":
            data["attendance"] = "Non"
        else:
            return "Répondez *1* (Oui, je vends) ou *2* (Non, je ne vends pas) :", None

        session["step"] = "comment"
        return (
            "Avez-vous un problème aujourd'hui ?\n\n"
            "1️⃣ Problème Produit\n"
            "2️⃣ Problème Relation / micro-distributeur\n"
            "3️⃣ Problème Revenu / paiement\n"
            "4️⃣ Motivation / formation\n"
            "5️⃣ Problème Équipement\n"
            "6️⃣ Aucun problème\n"
            "0️⃣ Autre\n\n"
            "Répondez avec le *numéro* correspondant."
        ), None

    # ── ÉTAPE 4 : Commentaire ─────────────────────────────────────────────────
    if step == "comment":
        if body not in ISSUE_MAP:
            return "Répondez avec un numéro entre 0 et 6 :", None

        categorie, prime = ISSUE_MAP[body]
        data["categorie"] = categorie
        data["prime"]     = prime
        session["step"]   = "done"

        if body == "6":
            # Pas de problème → on enregistre directement
            row = _build_row(phone, data, commentaire="")
            reset_session(phone)
            return (
                "✅ *Merci, votre présence a été enregistrée !*\n\n"
                "Bonne journée de vente ! 🙏\n\n"
                "_Envoyez MENU pour accéder au support à tout moment._"
            ), row

        return (
            f"📝 Vous avez signalé : *{categorie}*\n\n"
            "Décrivez brièvement votre problème _(optionnel)_ :\n"
            "_(Envoyez un espace ou un tiret si vous n'avez rien à ajouter)_"
        ), None

    # ── ÉTAPE 5 : Fin ─────────────────────────────────────────────────────────
    if step == "done":
        commentaire = body if body not in ["-", " ", ""] else ""
        row = _build_row(phone, data, commentaire=commentaire)
        reset_session(phone)
        return (
            "✅ *Merci, votre problème a bien été reçu !*\n\n"
            "Notre équipe l'examinera et fera un suivi via votre "
            "micro-distributeur ou superviseur commercial. 🙏\n\n"
            "_Envoyez MENU pour accéder au support à tout moment._"
        ), row

    # ── MENU (commande spéciale) ───────────────────────────────────────────────
    if body.upper() == "MENU":
        reset_session(phone)
        return _menu(), None

    # Fallback
    reset_session(phone)
    return _menu(), None


def _menu() -> str:
    return (
        "📋 *Company Vendor Support — Menu*\n\n"
        "Répondez avec un numéro :\n\n"
        "1️⃣ J'ai un problème produit\n"
        "2️⃣ J'ai un problème micro-distributeur\n"
        "3️⃣ J'ai une question revenu ou paiement\n"
        "4️⃣ Je veux une formation ou conseils de vente\n"
        "5️⃣ J'ai un problème d'équipement\n"
        "6️⃣ Je veux confirmer le prix du jour\n"
        "7️⃣ Je veux parler au support"
    )


def _build_row(phone: str, data: dict, commentaire: str) -> list:
    now = datetime.now()
    return [
        now.strftime("%d/%m/%Y"),          # Date
        now.strftime("%H:%M"),             # Heure
        phone,                             # Téléphone
        data.get("vendor_id", "—"),        # Vendor ID
        data.get("attendance", "—"),       # Présence
        data.get("categorie", "—"),        # Catégorie
        data.get("prime", ""),             # Pilier PRIME
        commentaire,                       # Commentaire
        "WhatsApp QR",                     # Source
    ]
