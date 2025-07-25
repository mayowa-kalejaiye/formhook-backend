"""
Service for sending emails via Resend API.
"""
import requests
from ..core.config import settings

def send_email(to_email: str, subject: str, html_content: str):
    """
    Send an email using the Resend API.
    Args:
        to_email (str): Recipient's email address
        subject (str): Email subject
        html_content (str): HTML content of the email
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
    # TODO: Add error handling, logging, and async support if needed
    return response.json()
