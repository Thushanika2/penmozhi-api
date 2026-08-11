import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

from flask import current_app

logger = logging.getLogger(__name__)


def is_email_configured():
    return bool(current_app.config.get("SMTP_HOST") and current_app.config.get("SMTP_FROM"))


def is_brevo_configured():
    return all(
        current_app.config.get(key)
        for key in ("BREVO_API_KEY", "BREVO_FROM_EMAIL", "BREVO_FROM_NAME")
    )


def _send_smtp(to_email, subject, text_body, html_body):
    if not is_email_configured():
        return False
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = current_app.config["SMTP_FROM"]
    message["To"] = to_email
    message.attach(MIMEText(text_body, "plain"))
    message.attach(MIMEText(html_body, "html"))
    try:
        with smtplib.SMTP(
            current_app.config["SMTP_HOST"], int(current_app.config.get("SMTP_PORT", 587)), timeout=20
        ) as server:
            if current_app.config.get("SMTP_USE_TLS", True):
                server.starttls()
            username = current_app.config.get("SMTP_USER")
            password = current_app.config.get("SMTP_PASSWORD")
            if username and password:
                server.login(username, password)
            server.sendmail(message["From"], [to_email], message.as_string())
        return True
    except Exception:
        logger.error("SMTP email delivery failed")
        return False


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    client_url = current_app.config.get("CLIENT_APP_URL", "http://localhost:3000").rstrip("/")
    reset_link = f"{client_url}/auth/reset-password?token={reset_token}"
    return _send_smtp(
        to_email,
        "Reset your Penmozhi password",
        f"Reset your Penmozhi password using this link (valid for 1 hour):\n{reset_link}",
        f'<p>Reset your Penmozhi password:</p><p><a href="{escape(reset_link)}">Reset password</a></p>',
    )


def send_cycle_invitation_email(to_email: str, invitation_code: str) -> bool:
    """Send a cycle invitation using Brevo without logging or returning the code."""
    if not is_brevo_configured():
        logger.error("Brevo cycle invitation email is not configured")
        return False

    # Lazy imports keep unrelated SMTP mail usable if a deployment has not yet installed the SDK.
    try:
        from brevo import Brevo
        from brevo.transactional_emails import (
            SendTransacEmailRequestSender,
            SendTransacEmailRequestToItem,
        )

        brand = "Penmozhi"
        safe_code = escape(invitation_code)
        html_body = f"""<!doctype html>
<html><body style="margin:0;background:#fff7f8;font-family:Arial,sans-serif;color:#33272a">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td align="center" style="padding:32px 16px">
<table role="presentation" width="100%" style="max-width:560px;background:#ffffff;border:1px solid #f3dfe4;border-radius:16px;overflow:hidden">
<tr><td style="background:#9f4865;color:#fff;padding:24px 32px;font-size:24px;font-weight:700">{brand}</td></tr>
<tr><td style="padding:32px"><p>Hi,</p><p>You’ve been invited to join {brand}.</p>
<p>Your invitation code is:</p><p style="font-size:32px;letter-spacing:8px;font-weight:700;text-align:center;background:#fff7f8;border-radius:12px;padding:18px">{safe_code}</p>
<p>Enter this code on our website to continue.</p><p>This code will expire in 10 minutes and can only be used once.</p>
<p style="color:#6f6266;font-size:14px">If you did not expect this invitation, you can safely ignore this email.</p>
<p>Thanks,<br>{brand}</p></td></tr></table></td></tr></table></body></html>"""
        text_body = (
            f"Hi,\n\nYou’ve been invited to join {brand}.\n\nYour invitation code is: "
            f"{invitation_code}\n\nEnter this code on our website to continue. This code will expire "
            f"in 10 minutes and can only be used once.\n\nIf you did not expect this invitation, "
            f"you can safely ignore this email.\n\nThanks,\n{brand}"
        )
        client = Brevo(api_key=current_app.config["BREVO_API_KEY"], timeout=15.0)
        client.transactional_emails.send_transac_email(
            subject=f"You’ve been invited to {brand}",
            html_content=html_body,
            text_content=text_body,
            sender=SendTransacEmailRequestSender(
                name=current_app.config["BREVO_FROM_NAME"],
                email=current_app.config["BREVO_FROM_EMAIL"],
            ),
            to=[SendTransacEmailRequestToItem(email=to_email)],
            request_options={"timeout_in_seconds": 15, "max_retries": 1},
        )
        return True
    except Exception:
        # Do not log the recipient, code, API key, or provider response body.
        logger.error("Brevo cycle invitation delivery failed")
        return False


def send_cycle_share_invite_email(to_email: str, owner_name: str, share_id: int) -> bool:
    """Retained only for compatibility with the retired legacy sharing controller."""
    return False
