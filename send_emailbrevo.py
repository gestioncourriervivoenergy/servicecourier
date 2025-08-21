import os
import psycopg2
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp-relay.brevo.com").strip()
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER").strip()
EMAIL_PASS = os.getenv("EMAIL_PASS").strip()
EMAIL_FROM = os.getenv("EMAIL_FROM", "gestioncourriervivoenergy@gmail.com").strip()

API_URL = os.getenv("API_URL").strip()
DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    # Connexion directe avec DATABASE_URL
    return psycopg2.connect(DATABASE_URL)

def send_email(ref):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
    """
    SELECT destinataire, email_destinataire, email_assistante, objet, statut, expediteur, date_recept, criticite, date_echeance
    FROM gestion_courier
    WHERE reference = %s
      AND DATE(date_echeance) >= DATE(NOW())
    """,
    (ref,)
)


    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        print(f"Référence {ref} non trouvée en base.")
        return

    destinataire, email_dest, email_cc, objet, statut, expediteur, date_recept, criticite, date_echeance = row
    if statut != "en_cours":
        print(f"Le courrier {ref} n'est pas en 'en_cours' (statut actuel: {statut}), email non envoyé.")
        return

    if not email_dest:
        print(f"Pas d'email pour {destinataire} ({ref})")
        return

    link = f"{API_URL}/api/traiter?ref={ref}"

    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = email_dest
    if email_cc:
        msg["Cc"] = email_cc
    msg["Subject"] = f"[Rappel] Courrier en retard : {objet}"

    body = f"""
Bonjour {destinataire},

Le courrier suivant n’a pas été traité dans les délais impartis :

Objet : {objet}
Référence : {ref}
Expéditeur : {expediteur}
Date de réception : {date_recept}
Criticité : {criticite}
Date limite de réponse : {date_echeance}

Cliquez sur ce lien pour le marquer comme TRAITÉ :
{link}

Merci !
"""
    msg.attach(MIMEText(body, "plain"))

    recipients = [email_dest]
    if email_cc:
        recipients.append(email_cc)
    recipients.append(EMAIL_FROM)

    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_FROM, recipients, msg.as_string())

    print(f"Email envoyé à {email_dest} pour la référence {ref}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python send_email.py <reference>")
    else:
        send_email(sys.argv[1])
