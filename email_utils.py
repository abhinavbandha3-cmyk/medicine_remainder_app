"""
Caregiver email alerts via Gmail SMTP.

Configure these environment variables before sending real emails:
    MAIL_ADDRESS       - the sending Gmail address
    MAIL_APP_PASSWORD  - a Gmail App Password (NOT your normal password)

If they are not set, send_caregiver_email() returns a friendly error instead
of crashing, so the rest of the app keeps working.
"""

import os
import smtplib
from email.mime.text import MIMEText

MAIL_ADDRESS = os.environ.get("MAIL_ADDRESS", "").strip()
MAIL_APP_PASSWORD = os.environ.get("MAIL_APP_PASSWORD", "").strip()


def send_caregiver_email(to_email: str, medicine_name: str = None, custom_body: str = None):
    if not MAIL_ADDRESS or not MAIL_APP_PASSWORD:
        return False, (
            "Email is not configured. Set MAIL_ADDRESS and MAIL_APP_PASSWORD "
            "environment variables (a Gmail App Password) to enable caregiver alerts."
        )

    if not to_email:
        return False, "No caregiver email address on file."

    subject = "Medicine Reminder Alert"
    if custom_body:
        body = custom_body
    elif medicine_name:
        body = f"Reminder: the patient is due to take '{medicine_name}'. Please check in with them."
    else:
        body = "This is a test alert from the Smart Medicine Reminder System."

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = MAIL_ADDRESS
    msg["To"] = to_email

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
            server.starttls()
            server.login(MAIL_ADDRESS, MAIL_APP_PASSWORD)
            server.sendmail(MAIL_ADDRESS, to_email, msg.as_string())
        return True, "Email sent successfully!"
    except Exception as e:
        return False, str(e)
