import os
import psycopg2
from dotenv import load_dotenv
from send_email import send_email
import logging

# --- Configuration ---
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def send_all_emails_en_cours():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT reference, delais_traitement FROM gestion_courier WHERE statut = 'en_cours'"
                )
                rows = cur.fetchall()
    except Exception as e:
        logging.error(f"Erreur connexion base: {e}")
        return

    if not rows:
        logging.info("Aucune donnée trouvée, arrêt du script.")
        return

    logging.info(f"{len(rows)} références à traiter")

    for ref, delai_traitement in rows:
        count = 2 if delai_traitement == 24 else 1
        for i in range(count):
            try:
                send_email(ref)
                logging.info(f"Email envoyé pour référence: {ref} (envoi {i+1}/{count})")
            except Exception as e:
                logging.error(f"Erreur envoi email pour {ref}: {e}")

if __name__ == "__main__":
    send_all_emails_en_cours()
