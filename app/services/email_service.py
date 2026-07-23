import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app

logger = logging.getLogger(__name__)


def is_email_configured():
    return bool(current_app.config.get("SMTP_HOST") and current_app.config.get("SMTP_FROM"))


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    if not is_email_configured():
        return False

    client_url = current_app.config.get("CLIENT_APP_URL", "http://localhost:3000").rstrip("/")
    reset_link = f"{client_url}/auth/reset-password?token={reset_token}"

    subject = "Reset your Penmozhi password"
    text_body = (
        "You requested a password reset for your Penmozhi account.\n\n"
        f"Reset your password using this link (valid for 1 hour):\n{reset_link}\n\n"
        "If you did not request this, you can ignore this email."
    )
    html_body = f"""
    <p>You requested a password reset for your Penmozhi account.</p>
    <p><a href="{reset_link}">Reset your password</a></p>
    <p>This link expires in 1 hour. If you did not request this, you can ignore this email.</p>
    """

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = current_app.config["SMTP_FROM"]
    message["To"] = to_email
    message.attach(MIMEText(text_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    host = current_app.config["SMTP_HOST"]
    port = int(current_app.config.get("SMTP_PORT", 587))
    username = current_app.config.get("SMTP_USER")
    password = current_app.config.get("SMTP_PASSWORD")
    use_tls = current_app.config.get("SMTP_USE_TLS", True)

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            if use_tls:
                server.starttls()
            if username and password:
                server.login(username, password)
            server.sendmail(message["From"], [to_email], message.as_string())
        return True
    except Exception:
        logger.exception("Failed to send password reset email to %s", to_email)
        return False
