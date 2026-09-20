import hashlib
import logging
import secrets
import smtplib
from email.message import EmailMessage

from app.config.settings import settings

logger = logging.getLogger(__name__)


def create_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(code: str) -> str:
    value = f"{settings.JWT_SECRET_KEY}:{code}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def send_otp_email(email: str, code: str, purpose: str = "login") -> None:
    is_register = purpose == "register"
    subject = "Your AgentIQ registration verification code" if is_register else "Your AgentIQ login code"
    action = "complete your account registration" if is_register else "sign in to your account"

    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        logger.info(
            f"🔑 [AGENTIQ OTP] Email: {email} | Code: {code} | Purpose: {purpose}. "
            f"(Expires in {settings.OTP_EXPIRE_MINUTES} min. To send real emails, set SMTP_HOST in .env)"
        )
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = email
    message.set_content(
        f"Welcome to AgentIQ!\n\n"
        f"Your verification code is: {code}\n\n"
        f"Enter this code to {action}. It expires in {settings.OTP_EXPIRE_MINUTES} minutes.\n\n"
        f"If you did not request this, please disregard this email."
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
        if settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USERNAME:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(message)