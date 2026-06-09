# -*- coding: utf-8 -*-
import os, json, logging
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
logger = logging.getLogger(__name__)
SCOPES         = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SHEET_NAME     = os.getenv("GOOGLE_SHEET_TAB", "Reponses Vendors")
HEADERS = [
   "Date", "Heure", "Telephone", "Vendor ID", "Nom Vendor",
   "Presence", "Categorie", "Pilier PRIME", "Commentaire", "Source"
]

def _get_service():
   creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
   if not creds_json:
       raise EnvironmentError("GOOGLE_CREDENTIALS_JSON manquant")
   info  = json.loads(creds_json)
   creds = Credentials.from_service_account_info(info, scopes=SCOPES)
   if not SPREADSHEET_ID:
       raise EnvironmentError("GOOGLE_SHEET_ID (SPREADSHEET_ID) manquant")
   return build("sheets", "v4", credentials=creds, cache_discovery=False)

def _ensure_headers(service):
   try:
       result = service.spreadsheets().values().get(
           spreadsheetId=SPREADSHEET_ID,
           range="{}!A1:J1".format(SHEET_NAME)
       ).execute()
       if not result.get("values"):
           service.spreadsheets().values().update(
               spreadsheetId=SPREADSHEET_ID,
               range="{}!A1".format(SHEET_NAME),
               valueInputOption="RAW",
               body={"values": [HEADERS]}
           ).execute()
           logger.info("En-tetes crees dans Google Sheets (%s)" % SHEET_NAME)
   except Exception as e:
       logger.warning("Impossible de verifier/creer en-tetes Google Sheets: %s" % e)
       raise

def append_row(row):
   if not SPREADSHEET_ID:
       logger.error("GOOGLE_SHEET_ID non défini — impossible d'ajouter une ligne")
       return False
   try:
       service = _get_service()
       _ensure_headers(service)
       service.spreadsheets().values().append(
           spreadsheetId=SPREADSHEET_ID,
           range="{}!A1".format(SHEET_NAME),
           valueInputOption="USER_ENTERED",
           insertDataOption="INSERT_ROWS",
           body={"values": [row]}
       ).execute()
       logger.info("Ligne ajoutee: %s" % (row,))
       return True
   except Exception as e:
       logger.error("Erreur Google Sheets: %s" % e, exc_info=True)
       return False