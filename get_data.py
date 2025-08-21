import os
import re
import logging
import requests
import psycopg2
import pandas as pd
from psycopg2.extras import execute_batch
from dotenv import load_dotenv
from clean import clean_email

# ======================================================
# 1. Configuration & Logging
# ======================================================
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

API_TOKEN = os.getenv("API_TOKEN", "").strip()
FORM_UID = os.getenv("FORM_UID", "").strip()
BASE_URL = os.getenv("BASE_URL", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
API_URL = os.getenv("API_URL", "").strip()

REQUIRED_ENV = [API_TOKEN, FORM_UID, BASE_URL, DATABASE_URL]
if not all(REQUIRED_ENV):
    raise ValueError("❌ Certaines variables d'environnement sont manquantes.")


# ======================================================
# 2. Extraction - Kobo API
# ======================================================
def get_kobo_data() -> list[dict]:
    """Récupère les données KoboToolbox via l’API."""
    url = f"{BASE_URL}/api/v2/assets/{FORM_UID}/data/?format=json"
    headers = {"Authorization": f"Token {API_TOKEN}"}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    results = response.json().get("results", [])
    logging.info(f"{len(results)} enregistrements récupérés depuis Kobo.")
    return results


# ======================================================
# 3. Connexion PostgreSQL
# ======================================================
def get_connection():
    """Retourne une connexion PostgreSQL via DATABASE_URL."""
    return psycopg2.connect(DATABASE_URL)


# ======================================================
# 5. Nettoyage - Délais de traitement
# ======================================================
def parse_delais_traitement(val):
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        match = re.match(r"(\d+)", val)
        return int(match.group(1)) if match else None
    return None


# ======================================================
# 6. Transformation - Destinataire
# ======================================================
def transform_destinataire(val: str | None) -> str | None:
    if not val or pd.isna(val):
        return None
    val = str(val).strip()
    val = val.replace("_and_", " and ").replace("_", " and ")
    return val


# ======================================================
# 7. Lecture des IDs existants
# ======================================================
def get_existing_ids() -> set[int]:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT _id FROM gestion_courier;")
        return {row[0] for row in cur.fetchall()}


# ======================================================
# 8. Chargement - PostgreSQL
# ======================================================
def load_data_to_db(data: list[dict]) -> None:
    existing_ids = get_existing_ids()
    logging.info(f"{len(existing_ids)} _id déjà présents dans la base.")

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
            statut = EXCLUDED.statut;
    """

    rows_to_insert = [
        (
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
            parse_delais_traitement(r.get("delais_traitement")),
        )
        for r in data if r.get("_id") not in existing_ids
    ]

    if not rows_to_insert:
        logging.info("Aucune nouvelle ligne à insérer.")
        return

    with get_connection() as conn, conn.cursor() as cur:
        execute_batch(cur, insert_query, rows_to_insert)
        conn.commit()
        logging.info(f"{len(rows_to_insert)} nouvelles lignes insérées ou mises à jour.")


# ======================================================
# 9. Orchestration ETL
# ======================================================
def run_pipeline():
    try:
        logging.info("🚀 Démarrage du pipeline ETL...")
        data = get_kobo_data()
        load_data_to_db(data)
        logging.info("✅ Pipeline terminé avec succès.")
    except Exception as e:
        logging.error(f"❌ Erreur lors de l'exécution du pipeline: {e}", exc_info=True)


if __name__ == "__main__":
    run_pipeline()
