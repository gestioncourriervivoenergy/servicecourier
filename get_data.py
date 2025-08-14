import os
import requests
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv
import re
import pandas as pd

# Charger les variables d'environnement
load_dotenv()

# --- CONFIGURATION ---
API_TOKEN = os.getenv("API_TOKEN", "").strip()
FORM_UID = os.getenv("FORM_UID", "").strip()
BASE_URL = os.getenv("BASE_URL", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()  # Doit utiliser aws-0-eu-north-1.pooler.supabase.com
API_URL = os.getenv("API_URL", "").strip()

if not API_TOKEN or not FORM_UID or not BASE_URL or not DATABASE_URL:
    raise ValueError("Certaines variables d'environnement sont manquantes.")

# --- 1. Extraction des données Kobo ---
def get_kobo_data():
    url = f"{BASE_URL}/api/v2/assets/{FORM_UID}/data/?format=json"
    headers = {"Authorization": f"Token {API_TOKEN}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["results"]

# --- 2. Connexion base PostgreSQL ---
def get_connection():
    """Connexion directe via DATABASE_URL"""
    return psycopg2.connect(DATABASE_URL)

# --- 3. Nettoyage des emails ---
def clean_email(email_str):
    if email_str is None or pd.isna(email_str) or str(email_str).strip() == "":
        return None

    email_str = str(email_str).strip().lower().replace(" ", "")
    corrections = {
        "_gmail_com": "@gmail.com",
        "_yahoo_com": "@yahoo.com",
        "_outlook_com": "@outlook.com"
    }
    for wrong, right in corrections.items():
        if wrong in email_str:
            email_str = email_str.replace(wrong, right)

    return email_str if "@" in email_str else None

# --- 4. Nettoyage delais_traitement ---
def parse_delais_traitement(val):
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        match = re.match(r"(\d+)", val)
        if match:
            return int(match.group(1))
    return None
def transform_destinataire(val):
    if not val or pd.isna(val):
        return None
    val = str(val).strip()

    # Exception: keep `_and_` as " and "
    val = val.replace("_and_", " and ")

    # Replace remaining underscores with " and "
    val = val.replace("_", " and ")

    return val
    

# --- 5. Chargement dans la base ---
def load_data_to_db(data):
    conn = get_connection()
    cur = conn.cursor()

    insert_query = """
        INSERT INTO gestion_courier (
            _id, formhub_uuid, start, "end", date_recept, expediteur, objet, reference,
            criticite, destinataire, action, date_transfert, date_echeance,
            assistante_en_charge, email_assistante, email_destinataire, statut,
            __version__, meta_instanceID, _xform_id_string, _uuid, meta_rootUuid,
            _attachments, _status, _geolocation, _submission_time, _tags, _notes,
            _submitted_by, delais_traitement
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (reference) DO UPDATE SET
            expediteur = EXCLUDED.expediteur,
            objet = EXCLUDED.objet,
            statut = EXCLUDED.statut
    """

    rows = []
    for r in data:
        rows.append((
            r.get("_id"),
            r.get("formhub/uuid"),
            r.get("start"),
            r.get("end"),
            r.get("date_recept"),
            r.get("expediteur"),
            r.get("objet"),
            r.get("reference"),
            r.get("criticite"),
            transform_destinataire(r.get("destinataire")),
            r.get("action"),
            r.get("date_transfert"),
            r.get("date_echeance"),
            r.get("assistante_en_charge"),
            clean_email(r.get("email_assistante")),
            clean_email(r.get("email_destinataire")),
            r.get("statut"),
            r.get("__version__"),
            r.get("meta/instanceID"),
            r.get("_xform_id_string"),
            r.get("_uuid"),
            r.get("meta/rootUuid"),
            r.get("_attachments"),
            r.get("_status"),
            r.get("_geolocation"),
            r.get("_submission_time"),
            r.get("_tags"),
            r.get("_notes"),
            r.get("_submitted_by"),
            parse_delais_traitement(r.get("delais_traitement"))
        ))

    execute_batch(cur, insert_query, rows)
    conn.commit()
    cur.close()
    conn.close()
    print(f"{len(rows)} lignes insérées ou mises à jour.")

# --- 6. Pipeline ETL ---
if __name__ == "__main__":
    print("Extraction des données Kobo...")
    data = get_kobo_data()
    print(f"{len(data)} enregistrements récupérés.")

    print("Chargement des données dans la base...")
    load_data_to_db(data)
