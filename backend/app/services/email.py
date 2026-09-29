import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings


logger = logging.getLogger(__name__)


def send_password_reset_email(email: str, token: str) -> None:
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password or not settings.password_reset_url:
        logger.warning("Password reset email is not configured; reset delivery skipped.")
        return

    reset_url = settings.password_reset_url.rstrip("/") + "?token=" + token
    message = EmailMessage()
    message["Subject"] = "Reset your AIME password"
    message["From"] = settings.smtp_from
    message["To"] = email
    message.set_content(
        "We received a request to reset your AIME password.\n\n"
        + "Use this link within 30 minutes:\n"
        + reset_url
        + "\n\nIf you did not request this, you can ignore this email."
    )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except Exception:
        logger.exception("Password reset email delivery failed.")
