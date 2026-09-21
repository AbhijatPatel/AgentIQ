import hashlib
import json
import logging
import random
import secrets
import smtplib
import socket
import time
import urllib.error
import urllib.request
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


def _send_via_resend(from_email: str, to_email: str, subject: str, html_content: str, text_content: str) -> None:
    api_key = settings.RESEND_API_KEY.strip()
    if not api_key:
        raise OTPConfigError("RESEND_API_KEY is not configured")

    sender = settings.effective_resend_from_email
    payload = {
        "from": sender,
        "to": [to_email],
        "subject": subject,
        "html": html_content,
        "text": text_content,
    }
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AgentIQ/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=settings.SMTP_TIMEOUT_SECONDS) as resp:
            resp_bytes = resp.read()
            if resp.status >= 400:
                raise OTPDeliveryError(f"Resend HTTP API returned status {resp.status}")
    except urllib.error.HTTPError as exc:
        raw_err = exc.read().decode("utf-8", errors="ignore")
        err_msg = ""
        try:
            parsed = json.loads(raw_err)
            err_msg = parsed.get("message") or parsed.get("error") or raw_err
        except Exception:
            err_msg = raw_err[:200]

        logger.error("Resend API error (HTTP %s): %s", exc.code, err_msg)
        if exc.code in (401, 403):
            raise OTPAuthError("Invalid or unauthorized Resend API Key. Please verify RESEND_API_KEY in Render.") from exc
        if exc.code == 422:
            raise OTPDeliveryError(f"Resend delivery failed: {err_msg}") from exc
        if exc.code == 429:
            raise OTPTransientError("Email provider rate limit reached. Please wait a moment and try again.") from exc
        raise OTPDeliveryError(f"Resend email delivery failed (status {exc.code})") from exc
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as exc:
        logger.error("Resend connection error: %s", type(exc).__name__)
        raise OTPTransientError("Could not connect to email delivery service. Please try again.") from exc
    except OTPDeliveryError:
        raise
    except Exception as exc:
        logger.error("Unexpected error during Resend delivery: %s", type(exc).__name__)
        raise OTPDeliveryError(f"Email delivery failed: {type(exc).__name__}") from exc


def _send_single_attempt(message: EmailMessage, host: str, port: int, use_ssl: bool) -> None:
    timeout = settings.SMTP_TIMEOUT_SECONDS
    username = settings.SMTP_USERNAME.strip()
    password = settings.sanitized_smtp_password

    if use_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=timeout) as smtp:
            smtp.ehlo()
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=timeout) as smtp:
            smtp.ehlo()
            if settings.SMTP_USE_TLS:
                smtp.starttls()
                smtp.ehlo()
            if username:
                smtp.login(username, password)
            smtp.send_message(message)


def send_otp_email(email: str, code: str, purpose: str = "login") -> None:
    subject = f"Your AgentIQ sign-in code: {code}"
    masked = _mask_email(email)

    if not settings.is_smtp_configured:
        logger.info(
            "🔑 [AGENTIQ OTP] Email: %s | Code: %s | Purpose: %s. "
            "(Expires in %s min. SMTP is not configured - set SMTP_HOST in .env for live emails)",
            masked,
            code,
            purpose,
            settings.OTP_EXPIRE_MINUTES,
        )
        return

    from_email = settings.effective_smtp_from_email
    from_header = (
        formataddr(("AgentIQ", from_email))
        if from_email
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

    if settings.RESEND_API_KEY.strip():
        logger.info("Sending OTP email to %s via Resend HTTPS API (port 443)", masked)
        _send_via_resend(
            from_email=from_email,
            to_email=email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )
        logger.info("Successfully sent OTP email to %s via Resend API", masked)
        return

    host = settings.SMTP_HOST.strip()
    primary_port = settings.SMTP_PORT
    primary_ssl = settings.SMTP_USE_SSL or primary_port == 465

    # Strategy: try primary config first, then fallback to the alternate SSL/STARTTLS port
    configs_to_try = [(primary_port, primary_ssl)]
    if primary_port == 587 or not primary_ssl:
        configs_to_try.append((465, True))
    else:
        configs_to_try.append((587, False))

    max_attempts = max(len(configs_to_try), settings.SMTP_MAX_RETRIES + 1)
    last_error: Exception | None = None

    for attempt in range(max_attempts):
        port, use_ssl = configs_to_try[attempt % len(configs_to_try)]
        mode_str = "SSL" if use_ssl else "STARTTLS"
        try:
            logger.info(
                "Attempting to send OTP email to %s via %s:%d (%s) (attempt %d/%d)",
                masked,
                host,
                port,
                mode_str,
                attempt + 1,
                max_attempts,
            )
            _send_single_attempt(message, host=host, port=port, use_ssl=use_ssl)
            logger.info("Successfully sent OTP email to %s via %s:%d (%s)", masked, host, port, mode_str)
            return
        except smtplib.SMTPAuthenticationError as exc:
            logger.error(
                "SMTP authentication failed for host=%s, user=%s (code=%s). Check SMTP credentials.",
                host,
                settings.SMTP_USERNAME,
                getattr(exc, "smtp_code", "unknown"),
            )
            raise OTPAuthError("SMTP server rejected email credentials. Please check App Password.") from exc
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
                "Transient error sending OTP email to %s via %s:%d on attempt %d/%d: %s",
                masked,
                host,
                port,
                attempt + 1,
                max_attempts,
                type(exc).__name__,
            )
            if attempt < max_attempts - 1:
                backoff = (1.0 ** attempt) + random.uniform(0.1, 0.4)
                time.sleep(backoff)
            else:
                break
        except Exception as exc:
            logger.error("Unexpected error during OTP email delivery: %s", type(exc).__name__)
            raise OTPDeliveryError(f"Email delivery failed: {type(exc).__name__}") from exc

    logger.error("All %d attempts to send OTP email to %s failed", max_attempts, masked)
    raise OTPTransientError("Email service is temporarily unavailable (outbound SMTP is blocked on cloud container). Please sign in/register with password, or set RESEND_API_KEY.") from last_error

