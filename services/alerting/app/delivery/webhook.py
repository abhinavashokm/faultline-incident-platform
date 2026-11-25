import asyncio
import hmac
import ipaddress
import json
import socket
from typing import Any

import httpx
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.delivery.models import Delivery, NotificationChannel
from app.delivery.schemas import WebhookChannelCreate


class WebhookDeliveryError(Exception):
    """A delivery failure safe to record or return to the caller."""


async def _resolve_public_address(host: str, port: int) -> str:
    records = await asyncio.get_running_loop().getaddrinfo(
        host, port, type=socket.SOCK_STREAM
    )
    addresses = [ipaddress.ip_address(record[4][0]) for record in records]
    for address in addresses:
        if not address.is_global or address.is_multicast or (
            isinstance(address, ipaddress.IPv6Address)
            and (address not in ipaddress.IPv6Network("2000::/3") or address.sixtofour is not None)
        ):
            raise WebhookDeliveryError("Webhook destination must resolve to public addresses")
    if not addresses:
        raise WebhookDeliveryError("Webhook destination could not be resolved")
    return str(addresses[0])


class WebhookChannelSender:
    async def send(self, channel: NotificationChannel, delivery: Delivery) -> None:
        await self.send_payload(channel, delivery.payload, str(delivery.id))

    async def send_payload(
        self, channel: NotificationChannel, payload: dict[str, Any], delivery_id: str
    ) -> None:
        key = settings.webhook_encryption_key
        if key is None or not channel.credentials_encrypted:
            raise WebhookDeliveryError("Webhook credentials are unavailable")

        try:
            credentials = json.loads(
                Fernet(key.get_secret_value()).decrypt(channel.credentials_encrypted.encode())
            )
            secret = credentials["signing_secret"].encode()
            auth = credentials["auth"]
            destination = WebhookChannelCreate(
                name=channel.name,
                channel_type="webhook",
                destination=channel.destination,
                auth=auth,
            )
        except (InvalidToken, ValueError, TypeError, KeyError, AttributeError):
            raise WebhookDeliveryError("Webhook configuration is invalid") from None

        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
        signature = hmac.digest(secret, body, "sha256").hex()
        url = httpx.URL(str(destination.destination))
        headers = {
            "Host": url.netloc.decode("ascii"),
            "Content-Type": "application/json",
            "X-Faultline-Delivery-Id": delivery_id,
            "X-Faultline-Signature": f"sha256={signature}",
        }
        if auth is not None:
            if auth["type"] == "bearer":
                headers["Authorization"] = f'Bearer {auth["value"]}'
            else:
                headers[auth["name"]] = auth["value"]

        try:
            async with asyncio.timeout(5):
                address = await _resolve_public_address(url.raw_host.decode("ascii"), url.port or 443)
                # Connect to the validated address while verifying TLS for the original host.
                request = httpx.Request(
                    "POST",
                    url.copy_with(host=address),
                    content=body,
                    headers=headers,
                    extensions={"sni_hostname": url.raw_host.decode("ascii")},
                )
                async with httpx.AsyncHTTPTransport(trust_env=False) as transport:
                    response = await transport.handle_async_request(request)
                    try:
                        if not response.is_success:
                            raise WebhookDeliveryError(
                                f"Webhook receiver returned HTTP {response.status_code}"
                            )
                    finally:
                        await response.aclose()
        except (TimeoutError, httpx.TimeoutException):
            raise WebhookDeliveryError("Webhook request timed out") from None
        except (OSError, httpx.RequestError, ValueError):
            raise WebhookDeliveryError("Could not connect to the webhook receiver") from None
