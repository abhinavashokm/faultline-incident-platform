import html
import logging
from typing import Any, Protocol

from app.core.config import settings
from app.delivery.email import EmailSender, mask_email, strip_crlf
from app.delivery.models import Delivery, NotificationChannel

logger = logging.getLogger(__name__)


class ChannelSender(Protocol):
    """Protocol for channel-specific senders."""

    async def send(self, channel: NotificationChannel, delivery: Delivery) -> None:
        """Send notification to the target channel."""
        ...


class EmailChannelSender:
    """Sender for channel_type == 'email' using EmailSender."""

    def __init__(self, email_sender: EmailSender) -> None:
        self.email_sender = email_sender

    async def send(self, channel: NotificationChannel, delivery: Delivery) -> None:
        payload = delivery.payload
        to_email = channel.destination
        project_id = payload.get("project_id", str(delivery.project_id))
        title = payload.get("title", "Unknown error")
        level = payload.get("level", "error")
        environment = payload.get("environment") or "unknown"
        release = payload.get("release") or "none"
        first_seen = payload.get("first_seen") or "N/A"
        issue_id = payload.get("issue_id", "")

        # Format Subject: [Faultline] New issue in <project>: <title>
        # Strip CR/LF to prevent header injection
        raw_subject = f"[Faultline] New issue in {project_id}: {title}"
        subject = strip_crlf(raw_subject)

        # Issue link
        base_url = (settings.frontend_base_url or "").rstrip("/")
        issue_link = f"{base_url}/issues/{issue_id}" if base_url and issue_id else ""

        # Plain text body
        text_body = (
            f"Faultline Alert: New Issue Detected\n\n"
            f"Project: {project_id}\n"
            f"Title: {title}\n"
            f"Level: {level}\n"
            f"Environment: {environment}\n"
            f"Release: {release}\n"
            f"First Seen (UTC): {first_seen}\n"
        )
        if issue_link:
            text_body += f"\nView Issue: {issue_link}\n"

        # HTML body
        escaped_title = html.escape(title)
        escaped_project = html.escape(str(project_id))
        escaped_level = html.escape(str(level))
        escaped_env = html.escape(str(environment))
        escaped_release = html.escape(str(release))
        escaped_first_seen = html.escape(str(first_seen))

        link_html = (
            f'<p><a href="{html.escape(issue_link)}" style="display:inline-block;padding:8px 16px;background-color:#2563eb;color:#ffffff;text-decoration:none;border-radius:4px;">View in Faultline</a></p>'
            if issue_link
            else ""
        )

        html_body = f"""<!DOCTYPE html>
<html>
<body style="font-family:sans-serif;line-height:1.5;color:#1e293b;">
  <h2 style="color:#dc2626;">[Faultline] New Issue Detected</h2>
  <table style="border-collapse:collapse;width:100%;max-width:600px;">
    <tr><td style="padding:6px 0;font-weight:bold;">Title:</td><td>{escaped_title}</td></tr>
    <tr><td style="padding:6px 0;font-weight:bold;">Project:</td><td>{escaped_project}</td></tr>
    <tr><td style="padding:6px 0;font-weight:bold;">Level:</td><td>{escaped_level}</td></tr>
    <tr><td style="padding:6px 0;font-weight:bold;">Environment:</td><td>{escaped_env}</td></tr>
    <tr><td style="padding:6px 0;font-weight:bold;">Release:</td><td>{escaped_release}</td></tr>
    <tr><td style="padding:6px 0;font-weight:bold;">First Seen:</td><td>{escaped_first_seen}</td></tr>
  </table>
  {link_html}
</body>
</html>"""

        logger.info(
            "Sending alert email to %s for delivery_id=%s",
            mask_email(to_email),
            delivery.id,
        )
        await self.email_sender.send(
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
