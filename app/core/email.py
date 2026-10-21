import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings


def send_email(*, to: str, subject: str, html_body: str, text_body: str | None = None) -> None:
    if settings.GMAIL_ADDRESS is None or settings.GMAIL_APP_PASSWORD is None:
        raise RuntimeError("Gmail credentials are not configured")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.GMAIL_ADDRESS
    msg["To"] = to
    if text_body is None:
        text_body = html_body.replace("<br>", "\n").replace("</p>", "\n\n")
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx, timeout=15) as smtp:
        smtp.login(settings.GMAIL_ADDRESS,
                   settings.GMAIL_APP_PASSWORD.get_secret_value())
        smtp.send_message(msg)
