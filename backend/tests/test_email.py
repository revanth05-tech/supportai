"""Tests for email delivery."""

import pytest
from unittest.mock import patch

from app.common.email import EmailService


@pytest.mark.anyio
async def test_send_email_returns_false_when_not_configured():
    service = EmailService()

    with patch(
        "app.common.email.settings.resend_api_key",
        None,
    ):
        result = await service.send_email(
            to="owner@example.com",
            subject="Test",
            html="<p>Hello</p>",
        )

    assert result is False


@pytest.mark.anyio
async def test_send_email_calls_resend():
    service = EmailService()

    with patch(
        "app.common.email.settings.resend_api_key",
        "test-api-key",
    ), patch(
        "app.common.email.resend.Emails.send",
        return_value={"id": "email-test-id"},
    ) as mock_send:

        result = await service.send_email(
            to="owner@example.com",
            subject="Test subject",
            html="<p>Hello</p>",
        )

    assert result is True

    mock_send.assert_called_once_with(
        {
            "from": "AI Support Agent <onboarding@resend.dev>",
            "to": ["owner@example.com"],
            "subject": "Test subject",
            "html": "<p>Hello</p>",
        }
    )


@pytest.mark.anyio
async def test_send_email_returns_false_when_resend_fails():
    service = EmailService()

    with patch(
        "app.common.email.settings.resend_api_key",
        "test-api-key",
    ), patch(
        "app.common.email.resend.Emails.send",
        side_effect=Exception("Resend failure"),
    ):

        result = await service.send_email(
            to="owner@example.com",
            subject="Test",
            html="<p>Hello</p>",
        )

    assert result is False