import os
import psycopg2
from dotenv import load_dotenv
from send_email import send_email  # ta fonction d'envoi email, à adapter si besoin

# Charger le fichier .env.local (même dossier que ce script)
load_dotenv()

DB_HOST = os.getenv("DB_HOST").strip()
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME").strip()
DB_USER = os.getenv("DB_USER").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD").strip()

def get_connection():
    print(f"Connexion avec DB_HOST={DB_HOST}, DB_USER={DB_USER}, DB_NAME={DB_NAME}")
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

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
