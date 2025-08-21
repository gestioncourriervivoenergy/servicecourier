import os
import psycopg2
from dotenv import load_dotenv
from send_email import send_email
import logging
from datetime import datetime

# --- Couleurs ANSI pour logs ---
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def log_info(msg):
    logging.info(f"{GREEN}{msg}{RESET}")

def log_warning(msg):
    logging.warning(f"{YELLOW}{msg}{RESET}")

def log_error(msg):
    logging.error(f"{RED}{msg}{RESET}")

# --- Chargement .env ---
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    if not DATABASE_URL:
        log_error("DATABASE_URL non défini dans le .env")
        raise ValueError("DATABASE_URL manquant")
    return psycopg2.connect(DATABASE_URL)

# --- Fonction principale ---
def send_all_emails_en_cours():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT reference, delais_traitement, date_echeance 
                    FROM gestion_courier 
                    WHERE statut = 'en_cours'
                    AND DATE(date_echeance) >= CURRENT_DATE
                    AND (last_email_sent_at IS NULL OR DATE(last_email_sent_at) < CURRENT_DATE)
                """)
                rows = cur.fetchall()
    except Exception as e:
        log_error(f"Erreur connexion base: {e}")
        return

    if not rows:
        log_info("Aucune donnée trouvée, arrêt du script.")
        return

    log_info(f"{len(rows)} références à traiter")

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                for ref, delai_traitement, date_echeance in rows:
                    count = 2 if delai_traitement == 24 else 1
                    for i in range(count):
                        try:
                            send_email(ref)
                            log_info(f"Email envoyé pour référence: {ref}, échéance: {date_echeance} (envoi {i+1}/{count})")
                            # Mise à jour last_email_sent_at
                            cur.execute("""
                                UPDATE gestion_courier
                                SET last_email_sent_at = NOW()
                                WHERE reference = %s
                            """, (ref,))
                            conn.commit()
                        except Exception as e:
                            log_error(f"Erreur envoi email pour référence: {ref}, échéance: {date_echeance} -> {e}")
    except Exception as e:
        log_error(f"Erreur mise à jour last_email_sent_at: {e}")

# --- Exécution ---
if __name__ == "__main__":
    send_all_emails_en_cours()
