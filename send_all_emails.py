import os
import psycopg2
from dotenv import load_dotenv
from send_email import send_email
import logging
from datetime import datetime
import smtplib

# --- Couleurs ANSI ---
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"

# --- Configuration logging ---
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

# --- Connexion DB ---
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

EMAIL_HOST = os.getenv("EMAIL_HOST").strip()
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("OUTLOOK_EMAIL").strip()
EMAIL_PASS = os.getenv("OUTLOOK_PASS").strip()

def get_connection():
    return psycopg2.connect(DATABASE_URL)

# --- Script principal ---
def send_all_emails_en_cours():
    # 1️⃣ Récupérer les courriers à traiter
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT reference, delais_traitement, date_echeance 
                    FROM gestion_courier 
                    WHERE statut='en_cours'
                      AND DATE(date_echeance) >= CURRENT_DATE
                      AND (last_email_sent_at IS NULL OR DATE(last_email_sent_at) < CURRENT_DATE)
                """)
                rows = cur.fetchall()
    except Exception as e:
        log_error(f"Erreur connexion base: {e}")
        return

    if not rows:
        log_info("Aucune nouvelle  donnée trouvée, arrêt du script.")
        return

    log_info(f"{len(rows)} références à traiter")

    # 2️⃣ Ouvrir une seule connexion SMTP pour tous les envois
    try:
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
    except Exception as e:
        log_error(f"Impossible de se connecter au serveur SMTP: {e}")
        return

    # 3️⃣ Envoyer les emails
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                for ref, delai_traitement, date_echeance in rows:
                    count = 2 if delai_traitement == 24 else 1
                    for i in range(count):
                        try:
                            send_email(ref, server)  # passer la connexion SMTP
                            log_info(
                                f"Email envoyé pour référence: {ref}, échéance: {date_echeance} (envoi {i+1}/{count})"
                            )
                            # mise à jour last_email_sent_at
                            cur.execute("""
                                UPDATE gestion_courier
                                SET last_email_sent_at = NOW()
                                WHERE reference = %s
                            """, (ref,))
                            conn.commit()
                        except Exception as e:
                            log_error(
                                f"Erreur envoi email pour référence: {ref}, échéance: {date_echeance} -> {e}"
                            )
    except Exception as e:
        log_error(f"Erreur mise à jour last_email_sent_at: {e}")

    # 4️⃣ Fermer la connexion SMTP
    server.quit()
    log_info("Tous les emails ont été traités.")

if __name__ == "__main__":
    send_all_emails_en_cours()
