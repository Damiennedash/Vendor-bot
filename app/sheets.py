# -*- coding: utf-8 -*-

import os, json, logging
# -*- coding: utf-8 -*-

import os
import json
import logging
from typing import Any, Dict, List

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
    "Periode",
    "Telephone",
    "Nom Vendor",
    "Depot",
    "Statut Vente",
    "Ventes FCFA",
    "FanXtra",
    "FanChoco",
    "FanVanille",
    "Categorie Probleme",
    "Pilier PRIME",
    "Commentaire",
    "Source",
]

HEADERS_VENDORS = [
    "Telephone",
    "Nom",
    "Depot",
    "Derniere declaration",
    "Dernieres ventes (FCFA)",
    "FanXtra",
    "FanChoco",
    "FanVanille",
    "Total pieces",
    "Date dernieres ventes",
]


def _load_credentials() -> Dict[str, Any]:
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
    if not SPREADSHEET_ID:
        raise EnvironmentError("GOOGLE_SHEET_ID manquant")

    info = _load_credentials()
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _ensure_sheet(service, sheet_name: str, headers: List[str]):
    """Crée l'onglet s'il n'existe pas et ajoute les en-têtes."""
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


def load_vendor_memory() -> Dict[str, Dict[str, Any]]:
    """Charge tous les vendors depuis Google Sheets au démarrage."""
    try:
        service = _get_service()
        _ensure_sheet(service, SHEET_VENDORS, HEADERS_VENDORS)
        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"{SHEET_VENDORS}!A2:K").execute()
        rows = result.get("values", [])
        memory: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            if not row:
                continue
            phone = row[0]
            memory[phone] = {
                "nom": row[1] if len(row) > 1 else "",
                "depot": row[2] if len(row) > 2 else "",
                "last_montant": row[4] if len(row) > 4 else "",
                "last_fanxtra": row[5] if len(row) > 5 else "",
                "last_fanchoco": row[6] if len(row) > 6 else "",
                "last_fanvanille": row[7] if len(row) > 7 else "",
                "last_pieces": row[8] if len(row) > 8 else "",
                "last_date": row[9] if len(row) > 9 else "",
            }
        logger.info("Mémoire chargée : %d vendors", len(memory))
        return memory
    except Exception:
        logger.exception("Erreur chargement mémoire vendors")
        return {}


def save_vendor(phone: str, nom: str, depot: str) -> None:
    """Enregistre ou met à jour un vendor dans Google Sheets."""
    try:
        service = _get_service()
        _ensure_sheet(service, SHEET_VENDORS, HEADERS_VENDORS)
        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"{SHEET_VENDORS}!A:A").execute()
        phones = [r[0] for r in result.get("values", []) if r]

        from datetime import datetime

        now = datetime.now().strftime("%d/%m/%Y %H:%M")

        if phone in phones:
            row_num = phones.index(phone) + 2  # A2 is first data row
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
                body={"values": [[phone, nom, depot, now, "", "", "", "", "", ""]]},
            ).execute()
        logger.info("Vendor sauvegardé : %s - %s", phone, nom)
    except Exception:
        logger.exception("Erreur sauvegarde vendor %s", phone)


def update_vendor_sales(phone: str, montant: Any, fanxtra: Any, fanchoco: Any) -> None:
    """Met à jour les dernières ventes d'un vendor (montant + produits)."""
    try:
        service = _get_service()
        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"{SHEET_VENDORS}!A:A").execute()
        phones = [r[0] for r in result.get("values", []) if r]
        if phone in phones:
            row_num = phones.index(phone) + 2
            total_pieces = ""  # calculate if needed
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{SHEET_VENDORS}!E{row_num}:G{row_num}",
                valueInputOption="USER_ENTERED",
                body={"values": [[montant, fanxtra, fanchoco]]},
            ).execute()
            logger.info("Ventes mises à jour pour %s", phone)
    except Exception:
        logger.exception("Erreur update ventes pour %s", phone)


def append_row(row: List[Any]) -> bool:
    """Ajoute une ligne de réponse dans l'onglet Réponses Vendors."""
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
