import os
import json
import logging
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SHEET_REPONSES = os.getenv("GOOGLE_SHEET_TAB", "Reponses Vendors")
SHEET_VENDORS  = "Vendors"

HEADERS_REPONSES = [
    "Date", "Heure", "Periode", "Telephone", "Nom Vendor", "Depot",
    "Statut Vente", "Ventes FCFA", "FanXtra", "FanChoco", "FanVanille",
    "Lieu de vente", "Categorie Probleme", "Pilier PRIME", "Commentaire", "Source"
]

HEADERS_VENDORS = [
    "Telephone", "Nom", "Depot", "Derniere declaration",
    "Dernieres ventes FCFA", "FanXtra", "FanChoco", "FanVanille",
    "Total pieces", "Date dernieres ventes"
]


# ──────────────────────────────────────────────────────────────
#  SERVICE SHEETS
# ──────────────────────────────────────────────────────────────
def _get_service():
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise EnvironmentError("GOOGLE_CREDENTIALS_JSON manquant")
    info  = json.loads(creds_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _ensure_sheet(service, sheet_name, headers):
    """Crée l'onglet et ses en-têtes s'ils n'existent pas encore."""
    meta     = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing = [s["properties"]["title"] for s in meta["sheets"]]

    if sheet_name not in existing:
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]}
        ).execute()
        logger.info("Onglet '{}' cree".format(sheet_name))

    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range="{}!A1:Z1".format(sheet_name)
    ).execute()

    if not result.get("values"):
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range="{}!A1".format(sheet_name),
            valueInputOption="RAW",
            body={"values": [headers]}
        ).execute()
        logger.info("En-tetes crees dans '{}'".format(sheet_name))


# ──────────────────────────────────────────────────────────────
#  LECTURE MÉMOIRE VENDORS
# ──────────────────────────────────────────────────────────────
def load_vendor_memory():
    """
    Charge tous les vendors depuis l'onglet 'Vendors'.
    Retourne un dict { telephone: { nom, depot, last_* } }
    """
    try:
        service = _get_service()
        _ensure_sheet(service, SHEET_VENDORS, HEADERS_VENDORS)

        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="{}!A2:J".format(SHEET_VENDORS)
        ).execute()

        rows   = result.get("values", [])
        memory = {}
        for row in rows:
            if not row:
                continue
            phone = str(row[0]).strip() if len(row) > 0 else ""
            if not phone:
                continue
            memory[phone] = {
                "nom":             str(row[1]).strip() if len(row) > 1 else "",
                "depot":           str(row[2]).strip() if len(row) > 2 else "",
                "last_montant":    str(row[4])         if len(row) > 4 else "0",
                "last_fanxtra":    str(row[5])         if len(row) > 5 else "0",
                "last_fanchoco":   str(row[6])         if len(row) > 6 else "0",
                "last_fanvanille": str(row[7])         if len(row) > 7 else "0",
                "last_pieces":     str(row[8])         if len(row) > 8 else "0",
                "last_date":       str(row[9])         if len(row) > 9 else "",
            }

        logger.info("Memoire chargee : {} vendors".format(len(memory)))
        return memory

    except Exception as e:
        logger.error("Erreur chargement memoire : {}".format(e))
        return {}


# ──────────────────────────────────────────────────────────────
#  UPSERT VENDOR — cœur du système
#  Crée OU met à jour la ligne complète d'un vendor.
#  Appelé dès que le vendor donne nom+dépôt, puis quand il
#  donne ses ventes pour compléter les colonnes E→J.
# ──────────────────────────────────────────────────────────────
def upsert_vendor(phone, nom, depot,
                  montant="", fanxtra="", fanchoco="", fanvanille="",
                  pieces="", date_vente=""):
    """
    Colonnes Vendors :
      A=Telephone  B=Nom  C=Depot  D=Derniere declaration
      E=Dernieres ventes FCFA  F=FanXtra  G=FanChoco  H=FanVanille
      I=Total pieces  J=Date dernieres ventes
    """
    try:
        service = _get_service()
        _ensure_sheet(service, SHEET_VENDORS, HEADERS_VENDORS)

        # Lire colonne A pour localiser le vendor
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="{}!A:A".format(SHEET_VENDORS)
        ).execute()
        phones = [str(r[0]).strip() if r else "" for r in result.get("values", [])]

        now_str  = datetime.now().strftime("%d/%m/%Y %H:%M")
        row_data = [
            phone, nom, depot, now_str,
            montant, fanxtra, fanchoco, fanvanille, pieces, date_vente,
        ]

        if phone in phones:
            row_num = phones.index(phone) + 1
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range="{}!A{}:J{}".format(SHEET_VENDORS, row_num, row_num),
                valueInputOption="USER_ENTERED",
                body={"values": [row_data]}
            ).execute()
            logger.info("Vendor mis a jour : {} — {}".format(phone, nom))
        else:
            service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range="{}!A1".format(SHEET_VENDORS),
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": [row_data]}
            ).execute()
            logger.info("Nouveau vendor cree : {} — {}".format(phone, nom))

        return True

    except Exception as e:
        logger.error("Erreur upsert_vendor : {}".format(e))
        return False


# ──────────────────────────────────────────────────────────────
#  ALIASES — gardés pour compatibilité avec main.py existant
# ──────────────────────────────────────────────────────────────
def save_vendor(phone, nom, depot):
    """Alias : enregistre nom + dépôt sans données de ventes."""
    return upsert_vendor(phone, nom, depot)


def update_vendor_sales(phone, montant, pieces, date,
                        fanxtra="0", fanchoco="0", fanvanille="0"):
    """Alias : met à jour uniquement les colonnes ventes."""
    try:
        service = _get_service()
        result  = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="{}!A:B".format(SHEET_VENDORS)
        ).execute()
        rows   = result.get("values", [])
        phones = [str(r[0]).strip() if r else "" for r in rows]
        noms   = [str(r[1]).strip() if len(r) > 1 else "" for r in rows]

        if phone not in phones:
            logger.warning("update_vendor_sales: vendor {} introuvable".format(phone))
            return False

        idx     = phones.index(phone)
        row_num = idx + 1
        nom     = noms[idx] if idx < len(noms) else ""
        depot   = ""

        # Récupérer le dépôt pour upsert complet
        full = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="{}!A{}:C{}".format(SHEET_VENDORS, row_num, row_num)
        ).execute()
        fv = full.get("values", [[]])[0]
        depot = str(fv[2]).strip() if len(fv) > 2 else ""

        return upsert_vendor(phone, nom, depot,
                             montant=montant, fanxtra=fanxtra,
                             fanchoco=fanchoco, fanvanille=fanvanille,
                             pieces=pieces, date_vente=date)

    except Exception as e:
        logger.error("Erreur update_vendor_sales : {}".format(e))
        return False


# ──────────────────────────────────────────────────────────────
#  ÉCRITURE DANS "Reponses Vendors"
# ──────────────────────────────────────────────────────────────
def append_row(row):
    """
    Ajoute une ligne dans l'onglet 'Reponses Vendors'.
    Appelé depuis main.py à chaque fin de conversation.
    """
    try:
        service = _get_service()
        _ensure_sheet(service, SHEET_REPONSES, HEADERS_REPONSES)

        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range="{}!A1".format(SHEET_REPONSES),
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]}
        ).execute()
        logger.info("Reponse enregistree pour {}".format(row[3] if len(row) > 3 else "?"))
        return True

    except Exception as e:
        logger.error("Erreur append_row : {}".format(e))
        return False
