import os
import json
import logging
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES         = ["https://www.googleapis.com/auth/spreadsheets"]
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


def _get_service():
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise EnvironmentError("GOOGLE_CREDENTIALS_JSON manquant")
    info  = json.loads(creds_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _ensure_sheet(service, sheet_name, headers):
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
    try:
        service = _get_service()
        _ensure_sheet(service, SHEET_VENDORS, HEADERS_VENDORS)
        result  = service.spreadsheets().values().get(
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
#  UPSERT VENDOR
#  - Sans ventes : enregistre juste nom + dépôt (étape identification)
#  - Avec ventes : met à jour les colonnes E→J (étape chiffres)
#  - is_today_sale=True  → ventes du jour   (J ai deja vendu)
#  - is_today_sale=False → ventes de la veille (Je vais vendre / Non)
#    Dans ce cas on met à jour Vendors mais en gardant la logique
# ──────────────────────────────────────────────────────────────
def upsert_vendor(phone, nom, depot,
                  montant="", fanxtra="", fanchoco="", fanvanille="",
                  pieces="", date_vente="", is_today_sale=True):
    try:
        service = _get_service()
        _ensure_sheet(service, SHEET_VENDORS, HEADERS_VENDORS)

        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="{}!A:A".format(SHEET_VENDORS)
        ).execute()
        phones  = [str(r[0]).strip() if r else "" for r in result.get("values", [])]
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M")

        # Si pas de données de ventes → on ne met à jour que nom/dépôt/date
        if not montant and not fanxtra:
            row_data = [phone, nom, depot, now_str, "", "", "", "", "", ""]
        else:
            row_data = [
                phone, nom, depot, now_str,
                montant, fanxtra, fanchoco, fanvanille, pieces, date_vente,
            ]

        if phone in phones:
            row_num = phones.index(phone) + 1

            if not montant and not fanxtra:
                # Mise à jour partielle : seulement A→D (nom, dépôt, date)
                service.spreadsheets().values().update(
                    spreadsheetId=SPREADSHEET_ID,
                    range="{}!A{}:D{}".format(SHEET_VENDORS, row_num, row_num),
                    valueInputOption="USER_ENTERED",
                    body={"values": [[phone, nom, depot, now_str]]}
                ).execute()
            else:
                # Mise à jour complète A→J
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


def save_vendor(phone, nom, depot):
    """Alias : identifie le vendor (sans ventes)."""
    return upsert_vendor(phone, nom, depot)


# ──────────────────────────────────────────────────────────────
#  ÉCRITURE DANS "Reponses Vendors"
#  Appelé UNE SEULE FOIS à la fin de chaque conversation
# ──────────────────────────────────────────────────────────────
def append_row(row):
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
        logger.info("Reponse enregistree pour {}".format(
            row[3] if len(row) > 3 else "?"))
        return True
    except Exception as e:
        logger.error("Erreur append_row : {}".format(e))
        return False
