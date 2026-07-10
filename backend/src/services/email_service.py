import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.core.config import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.user = settings.smtp_user
        self.password = settings.smtp_password
        self.from_email = settings.smtp_from_email
        self.use_tls = settings.smtp_use_tls

    def send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        if not self.host:
            logger.warning("SMTP host not configured. Email not sent.")
            logger.info(
                f"[DEV EMAIL to {to_email}] Subject: {subject} | Body: {html_body}"
            )
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email

            part = MIMEText(html_body, "html")
            msg.attach(part)

            server = smtplib.SMTP(self.host, self.port)
            if self.use_tls:
                server.starttls()
            if self.user and self.password:
                server.login(self.user, self.password)

            server.sendmail(self.from_email, to_email, msg.as_string())
            server.quit()

            logger.info(f"Successfully sent email to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            logger.info(
                f"[FALLBACK] Email content intended for {to_email}: {html_body}"
            )
            return False
