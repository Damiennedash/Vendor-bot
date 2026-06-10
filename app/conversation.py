# -*- coding: utf-8 -*-

from datetime import datetime

BRAND = "FANMILK TOGO"

ISSUE_MAP = {

    "1": ("Problème Produit",                   "Product"),

    "2": ("Problème Relation / micro-distrib",  "Relationship"),

    "3": ("Problème Revenu / paiement",         "Income"),

    "4": ("Motivation / formation",             "Motivation"),

    "5": ("Problème Équipement",                "Equipment"),

    "6": ("Confirmation prix du jour",          ""),

    "7": ("Demande support direct",             ""),

    "8": ("Aucun problème",                     ""),

}

SESSIONS = {}

MOTS_INVALIDES = [

    "oui", "non", "ok", "yes", "no", "menu", "bonjour", "bonsoir",

    "salut", "allo", "peut-etre", "1", "2", "3", "4", "5", "6", "7", "8",

    "bonjour fanmilk togo", "bonsoir fanmilk togo",

]


def _heure():

    return datetime.now().hour


def _matin():

    return _heure() < 13


def _salutation():

    return "Bonjour" if _matin() else "Bonsoir"


def _au_revoir(nom):

    if _matin():

        return "Bonne vente *{}* ! 💪\n\nVotre déclaration a bien été enregistrée.\n\nÀ tout à l'heure !".format(nom)

    else:

        return "Bonne soirée *{}* ! 🌙\n\nVotre déclaration a bien été enregistrée.\n\n*À demain !*".format(nom)


def get_session(phone):

    if phone not in SESSIONS:

        SESSIONS[phone] = {"step": "start", "data": {}}

    return SESSIONS[phone]


def reset_session(phone):

    SESSIONS[phone] = {"step": "start", "data": {}}


def handle_message(phone, body):

    body_raw = body.strip()

    body_low = body_raw.lower()

    session = get_session(phone)

    step = session["step"]

    data = session["data"]

    # Commande MENU → reset

    if body_low == "menu":

        reset_session(phone)

        session = get_session(phone)

        step = session["step"]

        data = session["data"]

    # ── DÉCLENCHEUR : premier message ou scan QR ──────────────────────────────

    if step == "start":

        session["step"] = "nom"

        return (

            "{} Champion ! Bienvenue sur *{}* Vendor Support. 🏆\n\n"

            "Pour enregistrer votre déclaration du jour,\n"

            "veuillez entrer votre *nom complet*."

        ).format(_salutation(), BRAND), None

    # ── ÉTAPE 1 : Nom ─────────────────────────────────────────────────────────

    if step == "nom":

        if len(body_raw) < 2 or body_low in MOTS_INVALIDES:

            return "Veuillez entrer votre *nom complet* s'il vous plaît.", None

        data["nom"] = body_raw

        session["step"] = "depot"

        return (

            "Merci *{}* ! 😊\n\n"

            "Quel est le nom de votre *dépôt / micro-distributeur* ?"

        ).format(body_raw), None

    # ── ÉTAPE 2 : Dépôt ───────────────────────────────────────────────────────

    if step == "depot":

        if len(body_raw) < 2:

            return "Veuillez entrer le nom de votre *dépôt*.", None

        data["depot"] = body_raw

        session["step"] = "vente_aujourd_hui"

        return (

            "Dépôt enregistré : *{}* ✅\n\n"

            "Vendez-vous *aujourd'hui* ?\n\n"

            "1 - Oui, je vends\n"

            "2 - Peut-être\n"

            "3 - Non, je ne vends pas"

        ).format(body_raw), None

    # ── ÉTAPE 3 : Vente aujourd'hui ───────────────────────────────────────────

    if step == "vente_aujourd_hui":

        if body_raw in ["1", "oui"]:

            data["vente_aujourd_hui"] = "Oui"

        elif body_raw in ["2", "peut-etre", "peut être", "peutetre"]:

            data["vente_aujourd_hui"] = "Peut-être"

        elif body_raw in ["3", "non"]:

            data["vente_aujourd_hui"] = "Non"

            session["step"] = "raison_non_vente"

            return (

                "Pourquoi ne vendez-vous pas aujourd'hui ?\n"

                "_(Décrivez brièvement la raison)_"

            ), None

        else:

            return (

                "Répondez avec le numéro :\n\n"

                "1 - Oui, je vends\n"

                "2 - Peut-être\n"

                "3 - Non, je ne vends pas"

            ), None

        # Oui ou Peut-être → ventes hier (montant)

        session["step"] = "ventes_hier_montant"

        if _matin():

            return (

                "Combien avez-vous vendu *hier* en FCFA ?\n"

                "_(Ex : 45000)_"

            ), None

        else:

            return (

                "Combien avez-vous vendu *aujourd'hui* en FCFA ?\n"

                "_(Ex : 45000)_"

            ), None

    # ── ÉTAPE 3b : Raison non-vente ───────────────────────────────────────────

    if step == "raison_non_vente":

        data["raison_non_vente"] = body_raw

        session["step"] = "ventes_hier_montant"

        if _matin():

            return (

                "Compris. Combien avez-vous vendu *hier* en FCFA ?\n"

                "_(Ex : 45000)_"

            ), None

        else:

            return (

                "Compris. Combien avez-vous vendu *aujourd'hui* en FCFA ?\n"

                "_(Ex : 45000)_"

            ), None

    # ── ÉTAPE 4 : Ventes montant FCFA ─────────────────────────────────────────

    if step == "ventes_hier_montant":

        data["ventes_montant"] = body_raw

        session["step"] = "ventes_hier_pieces"

        if _matin():

            return (

                "Combien de *pièces Fan* avez-vous vendues *hier* ?\n"

                "_(Ex : 12)_"

            ), None

        else:

            return (

                "Combien de *pièces Fan* avez-vous vendues *aujourd'hui* ?\n"

                "_(Ex : 12)_"

            ), None

    # ── ÉTAPE 5 : Ventes pièces Fan ───────────────────────────────────────────

    if step == "ventes_hier_pieces":

        data["ventes_pieces"] = body_raw

        session["step"] = "probleme"

        return _menu_text(), None

    # ── ÉTAPE 6 : Problème PRIME ──────────────────────────────────────────────

    if step == "probleme":

        if body_raw not in ISSUE_MAP:

            return _menu_text(), None

        categorie, prime = ISSUE_MAP[body_raw]

        data["categorie"] = categorie

        data["prime"] = prime

        nom = data.get("nom", "")

        if body_raw == "8":

            row = _build_row(phone, data, "")

            reset_session(phone)

            return _au_revoir(nom), row

        if body_raw == "6":

            row = _build_row(phone, data, "Demande prix du jour")

            reset_session(phone)

            return (

                "Votre demande de confirmation de prix a été transmise.\n\n"

                "Notre équipe vous répond rapidement. 🙏\n\n"

            ) + _au_revoir(nom), row

        if body_raw == "7":

            row = _build_row(phone, data, "Demande support direct")

            reset_session(phone)

            return (

                "Un agent vous contactera très prochainement. 🙏\n\n"

            ) + _au_revoir(nom), row

        session["step"] = "commentaire"

        return (

            "Vous avez signalé : *{}*\n\n"

            "Décrivez brièvement votre problème _(optionnel)_ :\n"

            "_(Envoyez un tiret - si vous n'avez rien à ajouter)_"

        ).format(categorie), None

    # ── ÉTAPE 7 : Commentaire ─────────────────────────────────────────────────

    if step == "commentaire":

        commentaire = "" if body_raw in ["-", ".", " "] else body_raw

        nom = data.get("nom", "")

        row = _build_row(phone, data, commentaire)

        reset_session(phone)

        return (

            "Merci ! Votre problème a bien été reçu. 🙏\n\n"

            "Notre équipe fera un suivi via votre micro-distributeur "

            "ou superviseur commercial.\n\n"

        ) + _au_revoir(nom), row

    # Fallback

    reset_session(phone)

    session = get_session(phone)

    session["step"] = "nom"

    return (

        "{} Champion ! Bienvenue sur *{}* Vendor Support. 🏆\n\n"

        "Veuillez entrer votre *nom complet*."

    ).format(_salutation(), BRAND), None


def _menu_text():

    return (

        "Avez-vous un problème pour atteindre vos objectifs aujourd'hui ?\n\n"

        "1 - J'ai un problème produit\n"

        "2 - J'ai un problème micro-distributeur / relation\n"

        "3 - J'ai une question revenu ou paiement\n"

        "4 - J'ai besoin d'une formation ou de conseils de vente\n"

        "5 - J'ai un problème d'équipement\n"

        "6 - Je veux confirmer le prix du jour\n"

        "7 - Je veux parler au support\n"

        "8 - Aucun problème\n\n"

        "Répondez avec le *numéro* correspondant."

    )


def _build_row(phone, data, commentaire):

    now = datetime.now()

    periode = "Matin" if now.hour < 13 else "Soir"

    return [

        now.strftime("%d/%m/%Y"),

        now.strftime("%H:%M"),

        periode,

        phone,

        data.get("nom", "-"),

        data.get("depot", "-"),

        data.get("vente_aujourd_hui", "-"),

        data.get("raison_non_vente", ""),

        data.get("ventes_montant", "-"),

        data.get("ventes_pieces", "-"),

        data.get("categorie", "-"),

        data.get("prime", ""),

        commentaire,

        "WhatsApp QR",

    ]
 