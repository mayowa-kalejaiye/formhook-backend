"""
Service for sending emails via Resend API.
"""

import requests
from ..core.config import settings
from sqlalchemy.orm import Session
from ..models.email_log import EmailLog

def send_email(to_email: str, subject: str, html_content: str):
    """
    Send an email using the Resend API and log the result to EmailLog.
    Args:
        to_email (str): Recipient's email address
        subject (str): Email subject
        html_content (str): HTML content of the email
        Optionally pass form_id and submission_id for logging.
    """
    url = "https://api.resend.com/emails"

    # Sanity checks to fail fast and provide clear logs when misconfigured
    if not settings.RESEND_API_KEY:
        raise Exception("RESEND_API_KEY is not configured. Set RESEND_API_KEY in environment.")
    if not settings.FROM_EMAIL:
        raise Exception("FROM_EMAIL is not configured. Set FROM_EMAIL in environment.")

    headers = {
        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "from": settings.FROM_EMAIL,
        "to": to_email,
        "subject": subject,
        "html": html_content
    }

    response = requests.post(url, json=data, headers=headers)

    # Raise on non-success so callers can handle/log it explicitly
    if not (200 <= response.status_code < 300):
        # Include response body for debugging
        err_text = f"Resend API returned {response.status_code}: {response.text}"
        print(f"Error sending email via Resend: {err_text}")
        response.raise_for_status()

    # Log to EmailLog if db, form_id, submission_id are provided
    def log_email(db: Session = None, form_id: str = None, submission_id: int = None):
        if db and form_id:
            status = "SENT"
            db.add(EmailLog(
                form_id=form_id,
                submission_id=submission_id,
                to_email=to_email,
                status=status
            ))
            db.commit()

    response.log_email = log_email  # Attach for caller to use
    return response
