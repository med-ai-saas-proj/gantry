from __future__ import annotations

import smtplib
from email.message import EmailMessage

import aiohttp
import pytest

pytestmark = pytest.mark.integration


async def _mailpit_messages(email_messages_url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(email_messages_url, timeout=8.0) as response:
            assert response.status == 200
            return await response.json()


@pytest.mark.asyncio
async def test_invitation_outbox_is_available_for_email_assertions(
    integration_stack,
) -> None:
    payload = await _mailpit_messages(integration_stack.email_messages_url)

    assert "messages" in payload


@pytest.mark.asyncio
async def test_invitation_email_can_be_delivered_and_asserted(
    integration_stack,
) -> None:
    message = EmailMessage()
    message["From"] = "noreply@gantry.test"
    message["To"] = "invitee@gantry.test"
    message["Subject"] = "Gantry integration invitation"
    message.set_content("Click http://localhost:3000/invite/test-token to accept.")

    smtp_host, smtp_port = integration_stack.mailpit_smtp_url
    with smtplib.SMTP(smtp_host, smtp_port, timeout=8) as smtp:
        smtp.send_message(message)

    payload = await _mailpit_messages(integration_stack.email_messages_url)
    messages = payload.get("messages", [])

    assert any(
        item.get("Subject") == "Gantry integration invitation"
        and item.get("To", [{}])[0].get("Address") == "invitee@gantry.test"
        for item in messages
    )
