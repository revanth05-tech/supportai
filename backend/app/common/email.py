"""Email delivery service."""

import resend

from app.core.config import settings


class EmailService:
    """Send application emails through Resend."""

    async def send_email(
        self,
        *,
        to: str,
        subject: str,
        html: str,
    ) -> bool:
        """Send an HTML email.

        Returns True when the request is submitted successfully.
        Returns False when email delivery is not configured or fails.
        """

        if not settings.resend_api_key:
            return False

        resend.api_key = settings.resend_api_key

        try:
            resend.Emails.send(
                {
                    "from": settings.email_from,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                }
            )
            return True
        except Exception:
            return False


email_service = EmailService()