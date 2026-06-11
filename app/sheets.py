# -*- coding: utf-8 -*-

import os
import json
import logging
from typing import Dict, Any, List

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SHEET_REPONSES = os.getenv("GOOGLE_SHEET_TAB", "Réponses Vendors")
SHEET_VENDORS = "Vendors"

HEADERS_REPONSES = [
    "Date",
    "Heure",
    "Période",
    "Téléphone",
    "Nom Vendor",
    "Dépôt",
    "Statut Vente",
    "Ventes (FCFA)",
    "Ventes (Pièces Fan)",
    "Catégorie Problème",
    "Pilier PRIME",
    "Commentaire",
    "Source",
]

HEADERS_VENDORS = [
    "Téléphone",
    "Nom",
    "Dépôt",
    "Dernière déclaration",
    "Dernières ventes (FCFA)",
    "Dernières pièces",
    "Date dernières ventes",
]


def _load_credentials() -> Dict[str, Any]:
    """Load service account info from env value or from a JSON filepath.

    Raises EnvironmentError if the credentials cannot be read/parsed.
    """
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise EnvironmentError(
            "GOOGLE_CREDENTIALS_JSON manquant. Mettez soit le contenu JSON, soit le chemin vers le fichier JSON dans cette variable d'environnement."
        )

    cj = creds_json.strip()
    try:
        if cj.startswith("{"):
            info = json.loads(cj)
        else:
            with open(cj, "r", encoding="utf-8") as fh:
                info = json.load(fh)
    except Exception as exc:
        raise EnvironmentError(f"Impossible de lire GOOGLE_CREDENTIALS_JSON : {exc}")

    return info


def _get_service():
    """Return a Google Sheets service object using service-account creds."""
    if not SPREADSHEET_ID:
        raise EnvironmentError("GOOGLE_SHEET_ID manquant")

    info = _load_credentials()
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _ensure_sheet(service, sheet_name: str, headers: List[str]):
    """Ensure the sheet (tab) exists and has headers."""
    try:
        meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        existing = [s["properties"]["title"] for s in meta.get("sheets", [])]

        if sheet_name not in existing:
            service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]},
            ).execute()
            logger.info("Onglet '%s' créé", sheet_name)

        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"{sheet_name}!A1:Z1").execute()
        if not result.get("values"):
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{sheet_name}!A1",
                valueInputOption="RAW",
                body={"values": [headers]},
            ).execute()
            logger.info("En-têtes créés dans '%s'", sheet_name)
    except Exception:
        logger.exception("Erreur lors de la vérification/création de l'onglet %s", sheet_name)
        raise


# ── Vendors memory helpers
def load_vendor_memory() -> Dict[str, Dict[str, Any]]:
    """Load Vendors sheet into an in-memory mapping {phone: {...}}."""
    try:
        service = _get_service()
        _ensure_sheet(service, SHEET_VENDORS, HEADERS_VENDORS)
        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"{SHEET_VENDORS}!A2:G").execute()
        rows = result.get("values", [])
        memory: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            if not row:
                continue
            phone = row[0]
            memory[phone] = {
                "nom": row[1] if len(row) > 1 else "",
                "depot": row[2] if len(row) > 2 else "",
                "last_date": row[6] if len(row) > 6 else "",
                "last_montant": row[4] if len(row) > 4 else "",
                "last_pieces": row[5] if len(row) > 5 else "",
            }
        logger.info("Mémoire chargée : %d vendors", len(memory))
        return memory
    except Exception:
        logger.exception("Erreur chargement mémoire vendors")
        return {}


def save_vendor(phone: str, nom: str, depot: str) -> None:
    """Insert or update a vendor row (A:D)."""
    try:
        service = _get_service()
        _ensure_sheet(service, SHEET_VENDORS, HEADERS_VENDORS)

        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"{SHEET_VENDORS}!A:A").execute()
        phones = [r[0] for r in result.get("values", []) if r]

        from datetime import datetime

        now = datetime.now().strftime("%d/%m/%Y %H:%M")

        if phone in phones:
            row_num = phones.index(phone) + 1 + 1  # +1 for header row, +1 because A2 is row 2
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{SHEET_VENDORS}!A{row_num}:D{row_num}",
                valueInputOption="USER_ENTERED",
                body={"values": [[phone, nom, depot, now]]},
            ).execute()
        else:
            service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{SHEET_VENDORS}!A1",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": [[phone, nom, depot, now, "", "", ""]]},
            ).execute()
        logger.info("Vendor sauvegardé : %s - %s", phone, nom)
    except Exception:
        logger.exception("Erreur sauvegarde vendor %s", phone)


def update_vendor_sales(phone: str, montant: str, pieces: str, date: str) -> None:
    """Update vendor sales columns E:G for a given phone."""
    try:
        service = _get_service()
        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"{SHEET_VENDORS}!A:A").execute()
        phones = [r[0] for r in result.get("values", []) if r]
        if phone in phones:
            row_num = phones.index(phone) + 1 + 1
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{SHEET_VENDORS}!E{row_num}:G{row_num}",
                valueInputOption="USER_ENTERED",
                body={"values": [[montant, pieces, date]]},
            ).execute()
            logger.info("Ventes mises à jour pour %s", phone)
    except Exception:
        logger.exception("Erreur update ventes pour %s", phone)


# ── Réponses ──────────────────────────────────────────────────────────────────
def append_row(row: List[Any]) -> bool:
    """Append a row to the responses sheet. Returns True on success."""
    try:
        service = _get_service()
        _ensure_sheet(service, SHEET_REPONSES, HEADERS_REPONSES)
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_REPONSES}!A1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ).execute()
        logger.info("Ligne ajoutée : %s", row)
        return True
    except Exception:
        logger.exception("Erreur Google Sheets append_row")
        return False
