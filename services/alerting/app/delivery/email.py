import asyncio
import html
import logging
import re
import smtplib
import ssl
from email.message import EmailMessage
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)


def mask_email(email: str) -> str:
    """Mask email for logging, e.g. alerts@faultline.io -> a***s@faultline.io."""
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = f"{local[:1]}***"
    else:
        masked_local = f"{local[0]}***{local[-1]}"
    return f"{masked_local}@{domain}"


def strip_crlf(value: str) -> str:
    """Strip carriage return and line feed characters to prevent header injection."""
    return re.sub(r"[\r\n]+", "", value).strip()


class EmailDeliveryError(Exception):
    """Domain error raised when sending an email fails."""


class EmailSender(Protocol):
    """Protocol for sending emails."""

    async def send(
        self,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str,
    ) -> None:
        """Send an email with both plain text and HTML alternatives."""
        ...


class SMTPEmailSender:
    """smtplib-based SMTP sender executed via asyncio.to_thread for async safety."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        from_email: str | None = None,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.host = host if host is not None else settings.smtp_host
        self.port = port if port is not None else settings.smtp_port
        self.from_email = from_email if from_email is not None else settings.email_from
        self.username = username if username is not None else settings.smtp_username
        self.password = password if password is not None else settings.smtp_password
        self.use_tls = use_tls if use_tls is not None else settings.smtp_use_tls
        self.timeout = timeout

    def _send_sync(self, message: EmailMessage, to_email: str) -> None:
        with smtplib.SMTP(host=self.host, port=self.port, timeout=self.timeout) as server:
            if self.use_tls:
                context = ssl.create_default_context()
                server.starttls(context=context)
            if self.username and self.password:
                server.login(self.username, self.password)
            server.send_message(message, from_addr=self.from_email, to_addrs=[to_email])

    async def send(
        self,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str,
    ) -> None:
        clean_subject = strip_crlf(subject)
        message = EmailMessage()
        message["From"] = self.from_email
        message["To"] = to_email
        message["Subject"] = clean_subject
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")

        try:
            await asyncio.to_thread(self._send_sync, message, to_email)
            logger.info("Email successfully sent to %s", mask_email(to_email))
        except Exception as exc:
            logger.error("Failed to send email to %s: %s", mask_email(to_email), exc)
            raise EmailDeliveryError(f"Failed to send email to {mask_email(to_email)}") from exc


_default_sender = SMTPEmailSender()


def get_email_sender() -> EmailSender:
    """Dependency provider for EmailSender."""
    return _default_sender
