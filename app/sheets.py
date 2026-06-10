# -*- coding: utf-8 -*-

import os
import json
import logging

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SHEET_NAME = os.getenv("GOOGLE_SHEET_TAB", "Réponses Vendors")

HEADERS = [
    "Date", "Heure", "Periode", "Telephone", "Nom Vendor", "Depot",
    "Vente Aujourd'hui", "Raison Non Vente", "Ventes Hier (FCFA)",
    "Categorie Probleme", "Pilier PRIME", "Commentaire", "Source"
]


def _get_service():
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise EnvironmentError("GOOGLE_CREDENTIALS_JSON manquant")
    info = json.loads(creds_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _ensure_headers(service):
    if not SPREADSHEET_ID:
        raise EnvironmentError("GOOGLE_SHEET_ID manquant")

    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A1:M1",
    ).execute()

    if not result.get("values"):
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A1",
            valueInputOption="RAW",
            body={"values": [HEADERS]},
        ).execute()
        logger.info("En-tetes crees dans Sheets")


def append_row(row):
    if not SPREADSHEET_ID:
        logger.error("GOOGLE_SHEET_ID manquant — impossible d'append")
        return False

    try:
        service = _get_service()
        _ensure_headers(service)

        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ).execute()

        logger.info("Ligne ajoutee: %s", row)
        return True

    except Exception as e:
        logger.error("Erreur Sheets: %s", e, exc_info=True)
        return False
