import hashlib
import logging
import random
import secrets
import smtplib
import socket
import time
from email.message import EmailMessage
from email.utils import formataddr

from app.config.settings import settings

logger = logging.getLogger(__name__)


class OTPDeliveryError(Exception):
    """Base exception for OTP email delivery failures."""


class OTPAuthError(OTPDeliveryError):
    """Raised when SMTP authentication fails (permanent error - bad credentials)."""


class OTPTransientError(OTPDeliveryError):
    """Raised when SMTP connection or network drops temporarily."""


class OTPConfigError(OTPDeliveryError):
    """Raised when SMTP configuration is invalid or missing."""


def create_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(code: str) -> str:
    value = f"{settings.JWT_SECRET_KEY}:{code}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = "*" * len(local)
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"


def _send_single_attempt(message: EmailMessage) -> None:
    host = settings.SMTP_HOST.strip()
    port = settings.SMTP_PORT
    timeout = settings.SMTP_TIMEOUT_SECONDS
    use_ssl = settings.SMTP_USE_SSL or port == 465

    if use_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=timeout) as smtp:
            smtp.ehlo()
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=timeout) as smtp:
            smtp.ehlo()
            if settings.SMTP_USE_TLS:
                smtp.starttls()
                smtp.ehlo()
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)


def send_otp_email(email: str, code: str, purpose: str = "login") -> None:
    subject = f"Your AgentIQ sign-in code: {code}"
    masked = _mask_email(email)

    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        logger.info(
            "🔑 [AGENTIQ OTP] Email: %s | Code: %s | Purpose: %s. "
            "(Expires in %s min. SMTP is not configured - set SMTP_HOST in .env for live emails)",
            masked,
            code,
            purpose,
            settings.OTP_EXPIRE_MINUTES,
        )
        return

    from_header = (
        formataddr(("AgentIQ", settings.SMTP_FROM_EMAIL))
        if settings.SMTP_FROM_EMAIL
        else "AgentIQ"
    )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_header
    message["To"] = email

    # Plain-text fallback
    text_content = (
        f"Your sign-in code is:\n\n"
        f"{code}\n\n"
        f"This code expires in {settings.OTP_EXPIRE_MINUTES} minutes. "
        f"If you didn't request it, you can ignore this email."
    )
    message.set_content(text_content)

    # Clean, responsive HTML template
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AgentIQ Sign-In Code</title>
</head>
<body style="margin: 0; padding: 0; background-color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased; color: #111827;">
  <table border="0" cellpadding="0" cellspacing="0" width="100%" style="table-layout: fixed; background-color: #ffffff;">
    <tr>
      <td align="center" style="padding: 48px 20px;">
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 480px; text-align: center;">
          <tr>
            <td style="padding-bottom: 36px;">
              <span style="font-size: 24px; font-weight: 700; letter-spacing: -0.5px; color: #0f172a;">AgentIQ</span>
            </td>
          </tr>
          <tr>
            <td style="font-size: 16px; line-height: 24px; color: #374151; padding-bottom: 24px;">
              Your sign-in code is:
            </td>
          </tr>
          <tr>
            <td align="center" style="padding-bottom: 28px;">
              <div style="display: inline-block; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px 32px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Courier New', monospace; font-size: 32px; font-weight: 700; letter-spacing: 8px; color: #0f172a;">
                {code}
              </div>
            </td>
          </tr>
          <tr>
            <td style="font-size: 14px; line-height: 20px; color: #64748b; padding-bottom: 36px;">
              This code expires in {settings.OTP_EXPIRE_MINUTES} minutes. If you didn't request it, you can ignore this email.
            </td>
          </tr>
          <tr>
            <td style="border-top: 1px solid #f1f5f9; padding-top: 24px; font-size: 12px; color: #94a3b8;">
              AgentIQ — Autonomous AI Research Platform
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    message.add_alternative(html_content, subtype="html")

    max_retries = max(0, settings.SMTP_MAX_RETRIES)
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            logger.info(
                "Attempting to send OTP email to %s via %s:%s (attempt %d/%d)",
                masked,
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                attempt + 1,
                max_retries + 1,
            )
            _send_single_attempt(message)
            logger.info("Successfully sent OTP email to %s", masked)
            return
        except smtplib.SMTPAuthenticationError as exc:
            # Permanent error: bad credentials or app password
            logger.error(
                "SMTP authentication failed for host=%s, user=%s (code=%s). Check SMTP credentials.",
                settings.SMTP_HOST,
                settings.SMTP_USERNAME,
                getattr(exc, "smtp_code", "unknown"),
            )
            raise OTPAuthError("SMTP server rejected email credentials") from exc
        except (
            smtplib.SMTPConnectError,
            smtplib.SMTPServerDisconnected,
            smtplib.SMTPResponseException,
            socket.timeout,
            TimeoutError,
            ConnectionError,
            OSError,
        ) as exc:
            last_error = exc
            logger.warning(
                "Transient error sending OTP email to %s on attempt %d/%d: %s",
                masked,
                attempt + 1,
                max_retries + 1,
                type(exc).__name__,
            )
            if attempt < max_retries:
                backoff = (1.5 ** attempt) + random.uniform(0.1, 0.5)
                time.sleep(backoff)
            else:
                break
        except Exception as exc:
            logger.error("Unexpected error during OTP email delivery: %s", type(exc).__name__)
            raise OTPDeliveryError(f"Email delivery failed: {type(exc).__name__}") from exc

    logger.error("All %d attempts to send OTP email to %s failed", max_retries + 1, masked)
    raise OTPTransientError("Email service is temporarily unavailable. Please try again.") from last_error
