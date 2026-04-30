import csv
import smtplib
import os
from email.message import EmailMessage
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

CSV_FILE = os.path.join(os.path.dirname(__file__), "data", "data.csv")

def send_emails():
    if not SMTP_USER or not SMTP_PASSWORD:
        print("SMTP credentials not found in .env")
        return

    print(f"Connecting to SMTP server at {SMTP_HOST}:{SMTP_PORT}...")
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        print("Successfully connected to SMTP server.")
    except Exception as e:
        print(f"Failed to connect to SMTP server: {e}")
        return

    try:
        with open(CSV_FILE, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            # Keep track of sent emails to avoid duplicates if necessary
            sent_emails = set()
            
            for row in reader:
                name = row.get("Name", "Participant").strip()
                email_address = row.get("Email", "").strip()
                
                if not email_address:
                    print(f"Skipping {name}, no email address provided.")
                    continue
                    
                if email_address in sent_emails:
                    print(f"Skipping {email_address}, already sent.")
                    continue
                
                msg = EmailMessage()
                msg['Subject'] = "Thank you for participating in Iyakkam!"
                msg['From'] = SMTP_USER
                msg['To'] = email_address
                
                body = f"""Dear {name},

Thank you for participating in Iyakkam!

Please fill out the feedback form to get your certificate:
https://certificate-pwa.vercel.app/

To login, use your registered email. Fill the form, download, and get your certificate to your email.

Best regards,
Iyakkam Team
by Valli Super Speciality Hospital"""
                msg.set_content(body)
                
                try:
                    server.send_message(msg)
                    print(f"Successfully sent email to {name} ({email_address})")
                    sent_emails.add(email_address)
                except Exception as e:
                    print(f"Failed to send email to {email_address}: {e}")

    except Exception as e:
        print(f"Failed to read CSV file: {e}")

    finally:
        server.quit()
        print("Finished sending all emails.")

if __name__ == "__main__":
    send_emails()
