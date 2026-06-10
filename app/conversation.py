# -*- coding: utf-8 -*-

from datetime import datetime

BRAND = "FANMILK TOGO"

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

SESSIONS = {}

# Mémoire permanente par numéro de téléphone

# { phone: { "nom": ..., "depot": ..., "last_montant": ..., "last_pieces": ..., "last_date": ... } }

VENDOR_MEMORY = {}

MOTS_INVALIDES = [

    "oui", "non", "ok", "yes", "no", "menu", "bonjour", "bonsoir",

    "salut", "allo", "peut-etre", "peut-être",

    "1", "2", "3", "4", "5", "6", "7", "8",

    "bonjour fanmilk togo", "bonsoir fanmilk togo", "fanmilk",

]


def _matin():

    return datetime.now().hour < 13


def _salutation():

    return "Bonjour" if _matin() else "Bonsoir"


def _today():

    return datetime.now().strftime("%d/%m/%Y")


def _au_revoir(nom):

    if _matin():

        return (

            "Bonne vente *{}* ! 💪\n\n"

            "Votre déclaration a bien été enregistrée.\n\n"

            "À tout à l'heure !"

        ).format(nom)

    else:

        return (

            "Bonne soirée *{}* ! 🌙\n\n"

            "Votre déclaration a bien été enregistrée.\n\n"

            "*À demain !*"

        ).format(nom)


def _is_nombre(text):

    return text.replace(" ", "").replace(",", "").replace(".", "").isdigit()


def _question_vente():

    """Question de vente universelle."""

    return (

        "Concernant vos ventes *aujourd'hui* :\n\n"

        "1 - Je vais vendre\n"

        "2 - J'ai déjà vendu\n"

        "3 - Je ne vends pas aujourd'hui"

    )


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

    if body_low == "menu":

        reset_session(phone)

        session = get_session(phone)

        step = session["step"]

        data = session["data"]

    # ── DÉCLENCHEUR ───────────────────────────────────────────────────────────

    if step == "start":

        mem = VENDOR_MEMORY.get(phone)

        if mem:

            # Vendor connu → saluer et poser la question de vente directement

            nom   = mem["nom"]

            depot = mem["depot"]

            data["nom"]   = nom

            data["depot"] = depot

            session["step"] = "vente_aujourd_hui"

            return (

                "{} Champion *{}* ! 🏆\n\n"

                "Dépôt : *{}*\n\n"

                "{}"

            ).format(_salutation(), nom, depot, _question_vente()), None

        # Nouveau vendor

        session["step"] = "nom"

        return (

            "{} Champion ! Bienvenue sur *{}* Vendor Support. 🏆\n\n"

            "Veuillez entrer votre *nom complet*."

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

            return "Veuillez entrer le nom de votre *dépôt* s'il vous plaît.", None

        data["depot"] = body_raw

        # Mémoriser nom + dépôt

        if phone not in VENDOR_MEMORY:

            VENDOR_MEMORY[phone] = {}

        VENDOR_MEMORY[phone]["nom"]   = data["nom"]

        VENDOR_MEMORY[phone]["depot"] = body_raw

        session["step"] = "vente_aujourd_hui"

        return (

            "Dépôt enregistré : *{}* ✅\n\n{}"

        ).format(body_raw, _question_vente()), None

    # ── ÉTAPE 3 : Vente aujourd'hui ───────────────────────────────────────────

    if step == "vente_aujourd_hui":

        if body_raw in ["1", "2"]:

            session["step"] = "ventes_montant"

            if body_raw == "1":

                # "Je vais vendre" → pas encore vendu → on demande les ventes HIER

                data["vente_aujourd_hui"] = "Je vais vendre"

                return (

                    "Combien avez-vous vendu *hier* en FCFA ?\n"

                    "_(Ex : 45000)_"

                ), None

            else:

                # "J'ai déjà vendu" → a vendu aujourd'hui → on demande les ventes AUJOURD'HUI

                data["vente_aujourd_hui"] = "J'ai déjà vendu"

                return (

                    "Combien avez-vous vendu *aujourd'hui* en FCFA ?\n"

                    "_(Ex : 45000)_"

                ), None

        elif body_raw == "3":

            # Non

            data["vente_aujourd_hui"] = "Non"

            if _matin():

                # Matin Non → ventes hier quand même

                session["step"] = "ventes_montant"

                return (

                    "Combien avez-vous vendu *hier* en FCFA ?\n"

                    "_(Ex : 45000)_"

                ), None

            else:

                # Soir Non → directement problèmes

                session["step"] = "probleme"

                return _menu_probleme(), None

        else:

            return _question_vente(), None

    # ── ÉTAPE 4 : Montant FCFA ────────────────────────────────────────────────

    if step == "ventes_montant":

        if not _is_nombre(body_raw):

            return "Veuillez entrer un *nombre valide* en FCFA.\n_(Ex : 45000)_", None

        data["ventes_montant"] = body_raw

        session["step"] = "ventes_pieces"

        if data.get("vente_aujourd_hui") == "Je vais vendre":

            return (

                "Combien de *pièces Fan* avez-vous vendues *hier* ?\n"

                "_(Uniquement un chiffre, ex : 12)_"

            ), None

        else:

            return (

                "Combien de *pièces Fan* avez-vous vendues *aujourd'hui* ?\n"

                "_(Uniquement un chiffre, ex : 12)_"

            ), None

    # ── ÉTAPE 5 : Pièces Fan ─────────────────────────────────────────────────

    if step == "ventes_pieces":

        if not body_raw.isdigit():

            return "Veuillez entrer *uniquement un chiffre*.\n_(Ex : 12)_", None

        data["ventes_pieces"] = body_raw

        # Mémoriser les ventes avec la date du jour

        if phone not in VENDOR_MEMORY:

            VENDOR_MEMORY[phone] = {}

        VENDOR_MEMORY[phone]["last_montant"] = data.get("ventes_montant", "0")

        VENDOR_MEMORY[phone]["last_pieces"]  = body_raw

        VENDOR_MEMORY[phone]["last_date"]    = _today()

        session["step"] = "probleme"

        return _menu_probleme(), None

    # ── ÉTAPE 6 : Problème PRIME ──────────────────────────────────────────────

    if step == "probleme":

        if body_raw not in ISSUE_MAP:

            return _menu_probleme(), None

        categorie, prime = ISSUE_MAP[body_raw]

        data["categorie"] = categorie

        data["prime"]     = prime

        nom = data.get("nom", "")

        if body_raw == "8":

            row = _build_row(phone, data, "")

            reset_session(phone)

            return _au_revoir(nom), row

        if body_raw == "6":

            row = _build_row(phone, data, "Demande prix du jour")

            reset_session(phone)

            return "Votre demande de prix a été transmise. 🙏\n\n" + _au_revoir(nom), row

        if body_raw == "7":

            row = _build_row(phone, data, "Demande support direct")

            reset_session(phone)

            return "Un agent vous contactera très prochainement. 🙏\n\n" + _au_revoir(nom), row

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

            "ou superviseur commercial.\n\n" +

            _au_revoir(nom)

        ), row

    # Fallback

    reset_session(phone)

    session = get_session(phone)

    session["step"] = "start"

    return handle_message(phone, body), None


def _menu_probleme():

    if _matin():

        return (

            "Avez-vous un problème pour atteindre vos objectifs *aujourd'hui* ?\n\n"

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

    else:

        return (

            "Avez-vous rencontré un problème *au cours de la journée* ?\n\n"

            "1 - Problème Produit\n"

            "2 - Problème Relation / micro-distributeur\n"

            "3 - Problème Revenu / paiement\n"

            "4 - Besoin de formation ou conseils de vente\n"

            "5 - Problème Équipement\n"

            "6 - Confirmer le prix du jour\n"

            "7 - Parler au support\n"

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

        data.get("ventes_montant", "0"),

        data.get("ventes_pieces", "0"),

        data.get("categorie", "-"),

        data.get("prime", ""),

        commentaire,

        "WhatsApp QR",

    ]
 