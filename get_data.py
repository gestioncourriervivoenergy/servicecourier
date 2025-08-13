import os
import requests
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv
import re
import pandas as pd
import socket

# Charger les variables d'environnement
load_dotenv()

# --- CONFIGURATION ---
API_TOKEN = os.getenv("API_TOKEN").strip()
FORM_UID = os.getenv("FORM_UID").strip()
BASE_URL = os.getenv("BASE_URL").strip()

DB_HOST = os.getenv("DB_HOST").strip()
DB_PORT = os.getenv("DB_PORT").strip()
DB_NAME = os.getenv("DB_NAME").strip()
DB_USER = os.getenv("DB_USER").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD").strip()

# --- 1. Extraction des données Kobo ---
def get_kobo_data():
    url = f"{BASE_URL}/api/v2/assets/{FORM_UID}/data/?format=json"
    headers = {"Authorization": f"Token {API_TOKEN}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["results"]

# --- 2. Connexion base PostgreSQL ---
def get_connection():
    ipv4_host = socket.gethostbyname(DB_HOST)  # force IPv4
    print(f"Connexion à PostgreSQL via IPv4: {ipv4_host}:{DB_PORT}")
    return psycopg2.connect(
        host=ipv4_host,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

# --- 3. Nettoyage des emails ---
def clean_email(email_str):
    if email_str is None:
        return None
    if pd.isna(email_str) or str(email_str).strip() == "":
        return None
    
    email_str = str(email_str).strip().lower().replace(" ", "")
    if "_gmail_com" in email_str:
        email_str = email_str.replace("_gmail_com", "@gmail.com")
    if "_yahoo_com" in email_str:
        email_str = email_str.replace("_yahoo_com", "@yahoo.com")
    if "_outlook_com" in email_str:
        email_str = email_str.replace("_outlook_com", "@outlook.com")
    
    if "@" in email_str:
        return email_str
    return None

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
            r.get("destinataire"),
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
