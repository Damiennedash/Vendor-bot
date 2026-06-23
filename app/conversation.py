import json
import os
from datetime import datetime, timedelta

BRAND = "FANMILK TOGO"

DEPOTS = {
    "1": "GERM DOSSEH",
    "2": "SUPER DEPOT",
    "3": "NBUKE RAMCO",
    "4": "NADONIELLA A",
    "5": "SAINT MARTIN",
    "6": "YEHONAM",
}

LIEUX = {
    "1": "Ecole",
    "2": "Marche",
    "3": "Eglise",
    "4": "Gare Routiere",
    "5": "Carrefour",
    "6": "Dans les quartiers",
    "7": "Autre",
}

ISSUE_MAP = {
    "1": ("Probleme Produit",        "Product"),
    "2": ("Probleme avec le gerant", "Relationship"),
    "3": ("Probleme de paiement",    "Income"),
    "4": ("Conseils de vente",       "Motivation"),
    "5": ("Probleme d equipement",   "Equipment"),
    "6": ("Demande support direct",  ""),
    "7": ("Aucun probleme",          ""),
}

MOTS_INVALIDES = [
    "oui", "non", "ok", "yes", "no", "menu",
    "bonjour", "bonsoir", "salut", "allo",
    "1", "2", "3", "4", "5", "6", "7",
    "bonjour fanmilk togo", "bonsoir fanmilk togo", "fanmilk",
]

_SESSIONS_FILE = "/tmp/sessions.json"


def _load_sessions():
    try:
        if os.path.exists(_SESSIONS_FILE):
            with open(_SESSIONS_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_sessions(sessions):
    try:
        with open(_SESSIONS_FILE, "w") as f:
            json.dump(sessions, f)
    except Exception:
        pass


SESSIONS = _load_sessions()

from .sheets import load_vendor_memory, upsert_vendor, append_row

VENDOR_MEMORY = None


def _get_memory():
    global VENDOR_MEMORY
    if VENDOR_MEMORY is None:
        try:
            VENDOR_MEMORY = load_vendor_memory()
        except Exception:
            VENDOR_MEMORY = {}
    return VENDOR_MEMORY


def _matin():
    return datetime.now().hour < 13


def _salutation():
    return "Bonjour" if _matin() else "Bonsoir"


def _today():
    return datetime.now().strftime("%d/%m/%Y")


def _yesterday():
    return (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")


def _au_revoir(nom):
    if _matin():
        return (
            "Bonne vente *" + nom + "* ! \U0001f4aa\n\n"
            "Votre declaration a bien ete enregistree.\n\n"
            "A tout a l heure !"
        )
    return (
        "Bonne soiree *" + nom + "* ! \U0001f319\n\n"
        "Votre declaration a bien ete enregistree.\n\n"
        "*A demain !*"
    )


def _is_nombre(text):
    return text.replace(" ", "").replace(",", "").replace(".", "").isdigit()


def _menu_depots():
    lines = ["Choisissez votre *depot* :", ""]
    for k, v in DEPOTS.items():
        lines.append(k + " - " + v)
    lines += ["", "Repondez avec le *numero* correspondant."]
    return "\n".join(lines)


def _menu_lieux(periode="aujourd hui"):
    lines = ["Ou avez-vous vendu *" + periode + "* ?", ""]
    for k, v in LIEUX.items():
        lines.append(k + " - " + v)
    lines += [
        "",
        "Vous pouvez choisir *plusieurs lieux*.",
        "_(Ex : 1 2 4 pour Ecole, Marche et Gare Routiere)_",
        "_(Tapez 7 si vous avez vendu ailleurs)_",
    ]
    return "\n".join(lines)


def _question_vente():
    lines = [
        "Concernant vos ventes *aujourd hui* :", "",
        "1 - Je vais vendre",
        "2 - J ai deja vendu",
        "3 - Je ne vends pas aujourd hui",
    ]
    return "\n".join(lines)


def _menu_probleme():
    if _matin():
        intro = "Avez-vous un probleme pour atteindre vos objectifs *aujourd hui* ?"
    else:
        intro = "Avez-vous rencontre un probleme *au cours de la journee* ?"
    lines = [
        intro, "",
        "1 - J ai un probleme produit",
        "2 - J ai un probleme avec mon gerant",
        "3 - J ai un probleme de paiement",
        "4 - J ai besoin de conseils de vente",
        "5 - J ai un probleme d equipement",
        "6 - Je veux parler au support",
        "7 - Aucun probleme", "",
        "Repondez avec le *numero* correspondant.",
    ]
    return "\n".join(lines)


def get_session(phone):
    if phone not in SESSIONS:
        SESSIONS[phone] = {"step": "start", "data": {}}
    return SESSIONS[phone]


def reset_session(phone):
    SESSIONS[phone] = {"step": "start", "data": {}}
    _save_sessions(SESSIONS)


def handle_message(phone, body):
    result = _handle_inner(phone, body)
    _save_sessions(SESSIONS)
    return result


def _build_row(phone, data, commentaire):
    """
    Construit la ligne pour l'onglet Reponses Vendors.
    Appelée UNE SEULE FOIS à la fin de la conversation.
    """
    now    = datetime.now()
    periode = "Matin" if now.hour < 13 else "Soir"
    return [
        now.strftime("%d/%m/%Y"),            # A Date
        now.strftime("%H:%M"),               # B Heure
        periode,                             # C Periode
        phone,                               # D Telephone
        data.get("nom",              "-"),   # E Nom Vendor
        data.get("depot",            "-"),   # F Depot
        data.get("vente_aujourd_hui","-"),   # G Statut Vente
        data.get("ventes_montant",   "0"),   # H Ventes FCFA
        data.get("fanxtra",          "0"),   # I FanXtra
        data.get("fanchoco",         "0"),   # J FanChoco
        data.get("fanvanille",       "0"),   # K FanVanille
        data.get("lieu_vente",       "-"),   # L Lieu de vente
        data.get("categorie",        "-"),   # M Categorie Probleme
        data.get("prime",            ""),    # N Pilier PRIME
        commentaire,                         # O Commentaire
        "WhatsApp QR",                       # P Source
    ]


def _handle_inner(phone, body):
    body_raw = body.strip()
    body_low = body_raw.lower()
    session  = get_session(phone)
    step     = session["step"]
    data     = session["data"]

    if body_low == "menu":
        reset_session(phone)
        session = get_session(phone)
        step    = session["step"]
        data    = session["data"]

    # ══════════════════════════════════════════════════════════
    #  START — 1er message reçu
    #  ✅ On enregistre dans Vendors IMMÉDIATEMENT (nom + dépôt)
    #  Sans ventes → pas de données biaisées
    # ══════════════════════════════════════════════════════════
    if step == "start":
        mem = _get_memory().get(phone)
        if mem and mem.get("nom") and mem.get("depot"):
            nom   = mem["nom"]
            depot = mem["depot"]
            data["nom"]   = nom
            data["depot"] = depot
            # ✅ MAJ Vendors : seulement nom + dépôt + date (PAS les ventes)
            upsert_vendor(phone, nom, depot)
            session["step"] = "vente_aujourd_hui"
            return (
                _salutation() + " Champion *" + nom + "* ! \U0001f3c6\n\n"
                "Depot : *" + depot + "*\n\n"
                + _question_vente()
            ), None

        session["step"] = "nom"
        return (
            _salutation() + " Champion ! Bienvenue sur *" + BRAND + "* Vendor Support. \U0001f3c6\n\n"
            "Veuillez entrer votre *nom*."
        ), None

    # ══════════════════════════════════════════════════════════
    #  NOM
    # ══════════════════════════════════════════════════════════
    if step == "nom":
        if len(body_raw) < 2 or body_low in MOTS_INVALIDES:
            return "Veuillez entrer votre *nom* s il vous plait.", None
        data["nom"]     = body_raw
        session["step"] = "depot"
        return "Merci *" + body_raw + "* ! \U0001f60a\n\n" + _menu_depots(), None

    # ══════════════════════════════════════════════════════════
    #  DEPOT
    #  ✅ Vendors mis à jour : nom + dépôt seulement (PAS les ventes)
    # ══════════════════════════════════════════════════════════
    if step == "depot":
        if body_raw not in DEPOTS:
            return _menu_depots(), None
        depot_nom     = DEPOTS[body_raw]
        data["depot"] = depot_nom
        nom           = data.get("nom", "")
        mem           = _get_memory()
        if phone not in mem:
            mem[phone] = {}
        mem[phone]["nom"]   = nom
        mem[phone]["depot"] = depot_nom
        # ✅ Vendors : nom + dépôt uniquement
        upsert_vendor(phone, nom, depot_nom)
        session["step"] = "vente_aujourd_hui"
        return "Depot enregistre : *" + depot_nom + "* \u2705\n\n" + _question_vente(), None

    # ══════════════════════════════════════════════════════════
    #  VENTE AUJOURD'HUI
    # ══════════════════════════════════════════════════════════
    if step == "vente_aujourd_hui":
        mem          = _get_memory().get(phone, {})
        last_date    = mem.get("last_date", "")
        deja_declare = last_date in [_today(), _yesterday()]

        if body_raw == "1":
            # "Je vais vendre" → chiffres = VENTES DE LA VEILLE
            data["vente_aujourd_hui"] = "Je vais vendre"
            data["lieu_vente"]        = "-"
            data["is_today_sale"]     = False  # ← ventes d'hier
            if deja_declare:
                data["ventes_montant"] = mem.get("last_montant",    "0")
                data["fanxtra"]        = mem.get("last_fanxtra",    "0")
                data["fanchoco"]       = mem.get("last_fanchoco",   "0")
                data["fanvanille"]     = mem.get("last_fanvanille", "0")
                session["step"]        = "probleme"
                return "Ventes deja enregistrees \u2705\n\n" + _menu_probleme(), None
            data["periode_ventes"] = "hier"
            session["step"]        = "ventes_montant"
            return "Combien avez-vous vendu *hier* en FCFA ?\n_(Ex : 45000)_", None

        if body_raw == "2":
            # "J'ai deja vendu" → chiffres = VENTES D'AUJOURD'HUI
            data["vente_aujourd_hui"] = "J ai deja vendu"
            data["periode_ventes"]    = "aujourd hui"
            data["is_today_sale"]     = True   # ← ventes du jour
            session["step"]           = "ventes_montant"
            return "Combien avez-vous vendu *aujourd hui* en FCFA ?\n_(Ex : 45000)_", None

        if body_raw == "3":
            # "Je ne vends pas" → chiffres = VENTES DE LA VEILLE
            data["vente_aujourd_hui"] = "Non"
            data["lieu_vente"]        = "-"
            data["is_today_sale"]     = False  # ← ventes d'hier
            data["periode_ventes"]    = "hier"
            session["step"]           = "ventes_montant"
            return "Combien avez-vous vendu *hier* en FCFA ?\n_(Ex : 45000)_", None

        return _question_vente(), None

    # ══════════════════════════════════════════════════════════
    #  MONTANT
    # ══════════════════════════════════════════════════════════
    if step == "ventes_montant":
        if not _is_nombre(body_raw):
            return "Veuillez entrer un *nombre valide* en FCFA.\n_(Ex : 45000)_", None
        data["ventes_montant"] = body_raw
        session["step"]        = "ventes_fanxtra"
        periode                = data.get("periode_ventes", "hier")
        return "Combien de *FanXtra* avez-vous vendus *" + periode + "* ?\n_(Chiffre uniquement, ex : 12)_", None

    # ══════════════════════════════════════════════════════════
    #  FANXTRA
    # ══════════════════════════════════════════════════════════
    if step == "ventes_fanxtra":
        if not body_raw.isdigit():
            return "Veuillez entrer *uniquement un chiffre*.\n_(Ex : 12)_", None
        data["fanxtra"] = body_raw
        session["step"] = "ventes_fanchoco"
        periode         = data.get("periode_ventes", "hier")
        return "Combien de *FanChoco* avez-vous vendus *" + periode + "* ?\n_(Chiffre uniquement, ex : 8)_", None

    # ══════════════════════════════════════════════════════════
    #  FANCHOCO
    # ══════════════════════════════════════════════════════════
    if step == "ventes_fanchoco":
        if not body_raw.isdigit():
            return "Veuillez entrer *uniquement un chiffre*.\n_(Ex : 8)_", None
        data["fanchoco"] = body_raw
        session["step"]  = "ventes_fanvanille"
        periode          = data.get("periode_ventes", "hier")
        return "Combien de *FanVanille* avez-vous vendus *" + periode + "* ?\n_(Chiffre uniquement, ex : 6)_", None

    # ══════════════════════════════════════════════════════════
    #  FANVANILLE
    #  ✅ Vendors mis à jour avec les ventes
    #  ✅ is_today_sale indique si c'est aujourd'hui ou hier
    # ══════════════════════════════════════════════════════════
    if step == "ventes_fanvanille":
        if not body_raw.isdigit():
            return "Veuillez entrer *uniquement un chiffre*.\n_(Ex : 6)_", None

        data["fanvanille"] = body_raw
        fanxtra            = data.get("fanxtra",        "0")
        fanchoco           = data.get("fanchoco",       "0")
        fanvanille         = body_raw
        montant            = data.get("ventes_montant", "0")
        total_pieces       = str(int(fanxtra) + int(fanchoco) + int(fanvanille))
        nom                = data.get("nom",   "")
        depot              = data.get("depot", "")
        is_today           = data.get("is_today_sale", True)

        # ✅ MAJ mémoire locale (toujours — pour se souvenir des derniers chiffres)
        mem = _get_memory()
        if phone not in mem:
            mem[phone] = {}
        mem[phone].update({
            "last_montant":    montant,
            "last_fanxtra":    fanxtra,
            "last_fanchoco":   fanchoco,
            "last_fanvanille": fanvanille,
            "last_pieces":     total_pieces,
            "last_date":       _today(),
        })

        # ✅ MAJ Vendors avec les ventes (on passe is_today_sale pour info)
        upsert_vendor(
            phone, nom, depot,
            montant=montant,
            fanxtra=fanxtra,
            fanchoco=fanchoco,
            fanvanille=fanvanille,
            pieces=total_pieces,
            date_vente=_today(),
            is_today_sale=is_today,
        )

        periode         = data.get("periode_ventes", "hier")
        session["step"] = "lieu_vente"
        return _menu_lieux(periode), None

    # ══════════════════════════════════════════════════════════
    #  LIEU DE VENTE
    # ══════════════════════════════════════════════════════════
    if step == "lieu_vente":
        periode       = data.get("periode_ventes", "hier")
        choix         = body_raw.replace(",", " ").split()
        lieux_valides = [c for c in choix if c in LIEUX]
        if not lieux_valides:
            return _menu_lieux(periode), None
        lieux_noms = [LIEUX[c] for c in lieux_valides]
        if "7" in lieux_valides:
            lieux_noms              = [l for l in lieux_noms if l != "Autre"]
            data["lieu_vente_temp"] = ", ".join(lieux_noms) if lieux_noms else ""
            session["step"]         = "lieu_autre"
            return "Precisez le lieu :\n_(Ex : Bord de mer, Stade)_", None
        data["lieu_vente"] = ", ".join(lieux_noms)
        session["step"]    = "probleme"
        return _menu_probleme(), None

    # ══════════════════════════════════════════════════════════
    #  LIEU AUTRE
    # ══════════════════════════════════════════════════════════
    if step == "lieu_autre":
        existants          = data.get("lieu_vente_temp", "")
        data["lieu_vente"] = (existants + ", " + body_raw).strip(", ") if existants else body_raw
        session["step"]    = "probleme"
        return _menu_probleme(), None

    # ══════════════════════════════════════════════════════════
    #  PROBLEME
    # ══════════════════════════════════════════════════════════
    if step == "probleme":
        if body_raw not in ISSUE_MAP:
            return _menu_probleme(), None
        categorie, prime  = ISSUE_MAP[body_raw]
        data["categorie"] = categorie
        data["prime"]     = prime
        nom               = data.get("nom", "")

        if body_raw == "7":
            # ✅ Réponses Vendors écrit ici (fin de conversation)
            row = _build_row(phone, data, "")
            reset_session(phone)
            return _au_revoir(nom), row

        if body_raw == "6":
            row = _build_row(phone, data, "Demande support direct")
            reset_session(phone)
            return "Un agent vous contactera tres prochainement.\n\n" + _au_revoir(nom), row

        session["step"] = "commentaire"
        return (
            "Vous avez signale : *" + categorie + "*\n\n"
            "Decrivez brievement votre probleme _(optionnel)_ :\n"
            "_(Envoyez un tiret - si vous n avez rien a ajouter)_"
        ), None

    # ══════════════════════════════════════════════════════════
    #  COMMENTAIRE
    #  ✅ Réponses Vendors écrit ici (fin de conversation)
    # ══════════════════════════════════════════════════════════
    if step == "commentaire":
        commentaire = "" if body_raw in ["-", ".", " "] else body_raw
        nom         = data.get("nom", "")
        row         = _build_row(phone, data, commentaire)
        reset_session(phone)
        return (
            "Merci ! Votre probleme a bien ete recu.\n\n"
            "Notre equipe fera un suivi.\n\n"
            + _au_revoir(nom)
        ), row

    # ══════════════════════════════════════════════════════════
    #  FALLBACK
    # ══════════════════════════════════════════════════════════
    reset_session(phone)
    mem = _get_memory().get(phone)
    if mem and mem.get("nom") and mem.get("depot"):
        session                  = get_session(phone)
        session["step"]          = "vente_aujourd_hui"
        session["data"]["nom"]   = mem["nom"]
        session["data"]["depot"] = mem["depot"]
        upsert_vendor(phone, mem["nom"], mem["depot"])
        return (
            _salutation() + " Champion *" + mem["nom"] + "* ! \U0001f3c6\n\n"
            "Depot : *" + mem["depot"] + "*\n\n"
            + _question_vente()
        ), None

    session         = get_session(phone)
    session["step"] = "nom"
    return (
        _salutation() + " Champion ! Bienvenue sur *" + BRAND + "* Vendor Support. \U0001f3c6\n\n"
        "Veuillez entrer votre *nom*."
    ), None
