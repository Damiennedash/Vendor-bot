# -*- coding: utf-8 -*-

import re

from datetime import datetime

BRAND = "FANMILK TOGO"

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

SESSIONS = {}

MOTS_INVALIDES = [

    "oui", "non", "ok", "yes", "no", "menu", "bonjour", "bonsoir",

    "salut", "allo", "peut-etre", "1", "2", "3", "4", "5", "6", "7", "8",

]


def get_session(phone):

    if phone not in SESSIONS:

        SESSIONS[phone] = {"step": "start", "data": {}}

    return SESSIONS[phone]


def reset_session(phone):

    SESSIONS[phone] = {"step": "start", "data": {}}


def _salutation():

    h = datetime.now().hour

    return "Bonjour" if h < 13 else "Bonsoir"


def _is_trigger(body):

    """Detecte si c'est un scan QR ou premier message."""

    triggers = [

        "fanmilk", "checkin", "check-in", "check in",

        "presence", "présence", "bonjour", "bonsoir", "allô", "allo", "salut"

    ]

    b = body.lower()

    return any(t in b for t in triggers) or len(body.strip()) <= 5


def handle_message(phone, body):

    body_raw = body.strip()

    body_low = body_raw.lower()

    session = get_session(phone)

    step = session["step"]

    data = session["data"]

    # Commande MENU → reset

    if body_low == "menu":

        reset_session(phone)

        return _welcome(phone), None

    # ── DECLENCHEUR QR ou premier message ────────────────────────────────────

    if step == "start" or _is_trigger(body_raw) and step == "start":

        reset_session(phone)

        session = get_session(phone)

        session["step"] = "nom"

        return _welcome(phone), None

    # ── ETAPE 1 : Nom du vendor ───────────────────────────────────────────────

    if step == "nom":

        if len(body_raw) < 2 or body_low in MOTS_INVALIDES:

            return "Veuillez entrer votre *nom complet*.", None

        data["nom"] = body_raw

        session["step"] = "depot"

        return (

            "Merci *{}* !\n\n"

            "Quel est le nom de votre *depot / micro-distributeur* ?"

        ).format(body_raw), None

    # ── ETAPE 2 : Depot ───────────────────────────────────────────────────────

    if step == "depot":

        if len(body_raw) < 2:

            return "Veuillez entrer le nom de votre *depot*.", None

        data["depot"] = body_raw

        session["step"] = "vente_aujourd_hui"

        return (

            "Depot enregistre : *{}*\n\n"

            "Vendez-vous *aujourd'hui* ?\n\n"

            "1 - Oui, je vends\n"

            "2 - Peut-etre\n"

            "3 - Non, je ne vends pas"

        ).format(body_raw), None

    # ── ETAPE 3 : Vente aujourd'hui ───────────────────────────────────────────

    if step == "vente_aujourd_hui":

        if body_raw in ["1", "oui"]:

            data["vente_aujourd_hui"] = "Oui"

            session["step"] = "ventes_hier"

            return (

                "Combien avez-vous vendu *hier* ?\n\n"

                "_(Entrez le montant en FCFA, ex: 45000)_"

            ), None

        elif body_raw in ["2", "peut-etre", "peut etre"]:

            data["vente_aujourd_hui"] = "Peut-etre"

            session["step"] = "ventes_hier"

            return (

                "Combien avez-vous vendu *hier* ?\n\n"

                "_(Entrez le montant en FCFA, ex: 45000)_"

            ), None

        elif body_raw in ["3", "non"]:

            data["vente_aujourd_hui"] = "Non"

            session["step"] = "raison_non_vente"

            return (

                "Pourquoi ne vendez-vous pas aujourd'hui ?\n\n"

                "_(Decrivez brievement la raison)_"

            ), None

        else:

            return (

                "Repondez avec le numero :\n\n"

                "1 - Oui, je vends\n"

                "2 - Peut-etre\n"

                "3 - Non, je ne vends pas"

            ), None

    # ── ETAPE 3b : Raison non vente (si Non) ─────────────────────────────────

    if step == "raison_non_vente":

        data["raison_non_vente"] = body_raw

        session["step"] = "ventes_hier"

        return (

            "Compris. Combien avez-vous vendu *hier* ?\n\n"

            "_(Entrez le montant en FCFA, ex: 45000)_"

        ), None

    # ── ETAPE 4 : Ventes hier ─────────────────────────────────────────────────

    if step == "ventes_hier":

        data["ventes_hier"] = body_raw

        session["step"] = "probleme"

        return _menu_text(), None

    # ── ETAPE 5 : Probleme PRIME ──────────────────────────────────────────────

    if step == "probleme":

        if body_raw not in ISSUE_MAP:

            return _menu_text(), None

        categorie, prime = ISSUE_MAP[body_raw]

        data["categorie"] = categorie

        data["prime"] = prime

        if body_raw == "8":

            row = _build_row(phone, data, "")

            reset_session(phone)

            return (

                "Parfait ! Bonne journee de vente *{}* !\n\n"

                "Votre declaration a bien ete enregistree.\n\n"

                "*A demain !*"

            ).format(data.get("nom", "")), row

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

        session["step"] = "commentaire"

        return (

            "Vous avez signale : *{}*\n\n"

            "Decrivez brievement votre probleme _(optionnel)_ :\n"

            "_(Envoyez - si vous n'avez rien a ajouter)_"

        ).format(categorie), None

    # ── ETAPE 6 : Commentaire ─────────────────────────────────────────────────

    if step == "commentaire":

        commentaire = "" if body_raw in ["-", ".", " "] else body_raw

        row = _build_row(phone, data, commentaire)

        reset_session(phone)

        return (

            "Merci *{}*, votre declaration a bien ete enregistree !\n\n"

            "Notre equipe fera un suivi si necessaire.\n\n"

            "*A demain !*"

        ).format(data.get("nom", "")), row

    reset_session(phone)

    return _welcome(phone), None


def _welcome(phone):

    sal = _salutation()

    session = get_session(phone)

    session["step"] = "nom"

    return (

        "{} ! Bienvenue sur *{}* Vendor Support.\n\n"

        "Pour enregistrer votre declaration du jour, "

        "veuillez entrer votre *nom complet*."

    ).format(sal, BRAND), None


# Appel recursif corrige

def handle_message(phone, body):

    body_raw = body.strip()

    body_low = body_raw.lower()

    session = get_session(phone)

    step = session["step"]

    data = session["data"]

    if body_low == "menu":

        reset_session(phone)

        session = get_session(phone)

        data = session["data"]

        step = session["step"]

    # Declencheur QR / premier contact

    if step == "start":

        session["step"] = "nom"

        sal = _salutation()

        return (

            "{} ! Bienvenue sur *{}* Vendor Support.\n\n"

            "Pour enregistrer votre declaration du jour, "

            "veuillez entrer votre *nom complet*."

        ).format(sal, BRAND), None

    # NOM

    if step == "nom":

        if len(body_raw) < 2 or body_low in MOTS_INVALIDES:

            return "Veuillez entrer votre *nom complet* svp.", None

        data["nom"] = body_raw

        session["step"] = "depot"

        return (

            "Merci *{}* !\n\n"

            "Quel est le nom de votre *depot / micro-distributeur* ?"

        ).format(body_raw), None

    # DEPOT

    if step == "depot":

        if len(body_raw) < 2:

            return "Veuillez entrer le nom de votre *depot*.", None

        data["depot"] = body_raw

        session["step"] = "vente_aujourd_hui"

        return (

            "Depot : *{}*\n\n"

            "Vendez-vous *aujourd'hui* ?\n\n"

            "1 - Oui, je vends\n"

            "2 - Peut-etre\n"

            "3 - Non, je ne vends pas"

        ).format(body_raw), None

    # VENTE AUJOURD'HUI

    if step == "vente_aujourd_hui":

        if body_raw in ["1", "oui"]:

            data["vente_aujourd_hui"] = "Oui"

            session["step"] = "ventes_hier"

            return (

                "Combien avez-vous vendu *hier* ?\n"

                "_(Montant en FCFA, ex: 45000)_"

            ), None

        elif body_raw in ["2", "peut-etre", "peut etre"]:

            data["vente_aujourd_hui"] = "Peut-etre"

            session["step"] = "ventes_hier"

            return (

                "Combien avez-vous vendu *hier* ?\n"

                "_(Montant en FCFA, ex: 45000)_"

            ), None

        elif body_raw in ["3", "non"]:

            data["vente_aujourd_hui"] = "Non"

            session["step"] = "raison_non_vente"

            return (

                "Pourquoi ne vendez-vous pas aujourd'hui ?\n"

                "_(Decrivez brievement)_"

            ), None

        else:

            return (

                "Repondez :\n"

                "1 - Oui\n2 - Peut-etre\n3 - Non"

            ), None

    # RAISON NON VENTE

    if step == "raison_non_vente":

        data["raison_non_vente"] = body_raw

        session["step"] = "ventes_hier"

        return (

            "Compris. Combien avez-vous vendu *hier* ?\n"

            "_(Montant en FCFA, ex: 45000)_"

        ), None

    # VENTES HIER

    if step == "ventes_hier":

        data["ventes_hier"] = body_raw

        session["step"] = "probleme"

        return _menu_text(), None

    # PROBLEME PRIME

    if step == "probleme":

        if body_raw not in ISSUE_MAP:

            return _menu_text(), None

        categorie, prime = ISSUE_MAP[body_raw]

        data["categorie"] = categorie

        data["prime"] = prime

        if body_raw == "8":

            row = _build_row(phone, data, "")

            reset_session(phone)

            return (

                "Parfait ! Bonne journee *{}* !\n\n"

                "Declaration enregistree.\n\n*A demain !*"

            ).format(data.get("nom", "")), row

        if body_raw == "6":

            row = _build_row(phone, data, "Demande prix du jour")

            reset_session(phone)

            return ("Demande prix transmise.\n\n*A demain !*"), row

        if body_raw == "7":

            row = _build_row(phone, data, "Demande support direct")

            reset_session(phone)

            return ("Un agent vous contactera.\n\n*A demain !*"), row

        session["step"] = "commentaire"

        return (

            "Vous avez signale : *{}*\n\n"

            "Decrivez brievement _(optionnel)_ :\n"

            "_(Envoyez - pour ignorer)_"

        ).format(categorie), None

    # COMMENTAIRE

    if step == "commentaire":

        commentaire = "" if body_raw in ["-", ".", " "] else body_raw

        row = _build_row(phone, data, commentaire)

        reset_session(phone)

        return (

            "Merci *{}* ! Declaration enregistree.\n\n*A demain !*"

        ).format(data.get("nom", "")), row

    reset_session(phone)

    session = get_session(phone)

    session["step"] = "nom"

    sal = _salutation()

    return (

        "{} ! Bienvenue sur *{}* Vendor Support.\n\n"

        "Veuillez entrer votre *nom complet*."

    ).format(sal, BRAND), None


def _menu_text():

    return (

        "Avez-vous un probleme pour atteindre vos objectifs aujourd'hui ?\n\n"

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

        data.get("ventes_hier", "-"),

        data.get("categorie", "-"),

        data.get("prime", ""),

        commentaire,

        "WhatsApp QR",

    ]
 