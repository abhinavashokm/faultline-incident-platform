import logging
from email.message import EmailMessage
from typing import Protocol

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """Domain error raised when sending an email fails."""


class EmailSender(Protocol):
    """Adapter interface for sending emails."""

    async def send_verification_code(
        self,
        to_email: str,
        code: str,
        expires_in_minutes: int = 10,
    ) -> None:
        """Send a verification code email to the specified recipient."""
        ...


class SMTPEmailSender:
    """aiosmtplib-based SMTP implementation of EmailSender."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        from_email: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.host = host or settings.smtp_host
        self.port = port or settings.smtp_port
        self.from_email = from_email or settings.smtp_from
        self.timeout = timeout

    async def send_verification_code(
        self,
        to_email: str,
        code: str,
        expires_in_minutes: int = 10,
    ) -> None:
        message = EmailMessage()
        message["From"] = self.from_email
        message["To"] = to_email
        message["Subject"] = "Verify your email address - Faultline"
        message.set_content(
            f"Your Faultline verification code is: {code}\n\n"
            f"This code will expire in {expires_in_minutes} minutes.\n\n"
            f"If you did not request this verification code, please ignore this email.\n"
        )

        try:
            await aiosmtplib.send(
                message,
                hostname=self.host,
                port=self.port,
                timeout=self.timeout,
            )
            logger.info("Verification email successfully sent to %s", to_email)
        except Exception as exc:
            # Never log the raw code
            logger.error("Failed to send verification email to %s: %s", to_email, exc)
            raise EmailDeliveryError(
                f"Failed to send verification email to {to_email}"
            ) from exc


_default_sender = SMTPEmailSender()


def get_email_sender() -> EmailSender:
    """FastAPI dependency provider for EmailSender."""
    return _default_sender

