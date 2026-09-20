import hashlib
import logging
import secrets
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from app.config.settings import settings

logger = logging.getLogger(__name__)


def create_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(code: str) -> str:
    value = f"{settings.JWT_SECRET_KEY}:{code}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def send_otp_email(email: str, code: str, purpose: str = "login") -> None:
    subject = f"Your AgentIQ sign-in code: {code}"

    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        logger.info(
            f"🔑 [AGENTIQ OTP] Email: {email} | Code: {code} | Purpose: {purpose}. "
            f"(Expires in {settings.OTP_EXPIRE_MINUTES} min. To send real emails, set SMTP_HOST in .env)"
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

    # Clean, professional responsive HTML template
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
          <!-- Branding -->
          <tr>
            <td style="padding-bottom: 36px;">
              <span style="font-size: 24px; font-weight: 700; letter-spacing: -0.5px; color: #0f172a;">AgentIQ</span>
            </td>
          </tr>
          <!-- Main Prompt Text -->
          <tr>
            <td style="font-size: 16px; line-height: 24px; color: #374151; padding-bottom: 24px;">
              Your sign-in code is:
            </td>
          </tr>
          <!-- OTP Display Box -->
          <tr>
            <td align="center" style="padding-bottom: 28px;">
              <div style="display: inline-block; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px 32px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Courier New', monospace; font-size: 32px; font-weight: 700; letter-spacing: 8px; color: #0f172a;">
                {code}
              </div>
            </td>
          </tr>
          <!-- Expiry Notice -->
          <tr>
            <td style="font-size: 14px; line-height: 20px; color: #64748b; padding-bottom: 36px;">
              This code expires in {settings.OTP_EXPIRE_MINUTES} minutes. If you didn't request it, you can ignore this email.
            </td>
          </tr>
          <!-- Footer Divider & Title -->
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

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
        if settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USERNAME:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(message)