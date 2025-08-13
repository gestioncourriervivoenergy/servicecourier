import os
import psycopg2
from dotenv import load_dotenv
from send_email import send_email  # ta fonction d'envoi email

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def send_all_emails_en_cours():
    try:
        conn = get_connection()
    except Exception as e:
        print("Erreur connexion base:", e)
        return

    cur = conn.cursor()
    cur.execute("SELECT reference, delais_traitement FROM gestion_courier WHERE statut = 'en_cours'")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if len(rows) == 0:
        print("Aucune donnée trouvée, arrêt du script.")
        return

    print(f"{len(rows)} références à traiter")

    for ref, delai_traitement in rows:
        print(f"Envoi email pour référence: {ref}, delais_traitement: {delai_traitement}")
        if delai_traitement == 24:
            send_email(ref)
            send_email(ref)
        else:
            send_email(ref)

if __name__ == "__main__":
    send_all_emails_en_cours()
