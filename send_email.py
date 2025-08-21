import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import psycopg2

load_dotenv()

EMAIL_HOST = os.getenv("EMAIL_HOST").strip()
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("OUTLOOK_EMAIL").strip()
EMAIL_PASS = os.getenv("OUTLOOK_PASS").strip()
EMAIL_FROM = EMAIL_USER

API_URL = os.getenv("API_URL").strip()
DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def send_email(ref, server=None):
    """Envoie un email pour la référence donnée, utilise server SMTP si fourni."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT destinataire, email_destinataire, email_assistante, objet, statut, expediteur, date_recept, criticite, date_echeance
        FROM gestion_courier
        WHERE reference = %s
          AND DATE(date_echeance) >= CURRENT_DATE
    """, (ref,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        print(f"[INFO] Référence {ref} non trouvée.")
        return

    destinataire, email_dest, email_cc, objet, statut, expediteur, date_recept, criticite, date_echeance = row
    if statut != "en_cours":
        print(f"[INFO] Courrier {ref} n'est pas en 'en_cours' (statut: {statut})")
        return
    if not email_dest:
        print(f"[INFO] Pas d'email pour {destinataire} ({ref})")
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

    close_server = False
    if server is None:
        import smtplib
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        close_server = True

    try:
        server.sendmail(EMAIL_FROM, recipients, msg.as_string())
        print(f"[SUCCESS] Email envoyé à {email_dest} pour la référence {ref}")
    except Exception as e:
        print(f"[ERROR] Erreur envoi email pour {ref}: {e}")

    if close_server:
        server.quit()
