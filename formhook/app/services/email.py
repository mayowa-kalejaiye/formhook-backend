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
    # Log to EmailLog if db, form_id, submission_id are provided
    def log_email(db: Session = None, form_id: str = None, submission_id: int = None):
        if db and form_id:
            status = "SENT" if response.status_code == 200 else "FAILED"
            db.add(EmailLog(
                form_id=form_id,
                submission_id=submission_id,
                to_email=to_email,
                status=status
            ))
            db.commit()
    response.log_email = log_email  # Attach for caller to use
    return response
