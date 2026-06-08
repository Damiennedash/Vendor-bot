"""
Écriture en temps réel dans Google Sheets via Service Account.
"""

import os, json, logging
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES        = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SHEET_NAME     = os.getenv("GOOGLE_SHEET_TAB", "Réponses Vendors")

# En-têtes (créés automatiquement si la feuille est vide)
HEADERS = [
    "Date", "Heure", "Téléphone", "Vendor ID",
    "Présence", "Catégorie", "Pilier PRIME", "Commentaire", "Source"
]


def _get_service():
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise EnvironmentError("Variable GOOGLE_CREDENTIALS_JSON manquante")
    info  = json.loads(creds_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _ensure_headers(service):
    """Vérifie que la ligne 1 contient les en-têtes, sinon les crée."""
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A1:I1"
    ).execute()
    if not result.get("values"):
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A1",
            valueInputOption="RAW",
            body={"values": [HEADERS]}
        ).execute()
        logger.info("En-têtes créés dans Google Sheets ✅")


def append_row(row: list) -> bool:
    """Ajoute une ligne de données dans la feuille Google Sheets."""
    try:
        service = _get_service()
        _ensure_headers(service)
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]}
        ).execute()
        logger.info(f"Ligne ajoutée: {row} ✅")
        return True
    except Exception as e:
        logger.error(f"Erreur Google Sheets: {e}", exc_info=True)
        return False
