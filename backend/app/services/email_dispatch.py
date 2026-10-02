"""Email dispatch service for ContentBridge official emails."""

from __future__ import annotations

import logging
import smtplib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import anyio

from app.config import settings

log = logging.getLogger(__name__)


@dataclass(slots=True)
class EmailDispatchResult:
    success: bool
    recipient: str
    subject: str
    message_id: str
    sent_at: str
    delivery_mode: str  # "smtp" or "simulated"
    detail: str


def _send_sync(
    *,
    to_email: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
    cc_emails: list[str] | None = None,
    from_email: str | None = None,
) -> EmailDispatchResult:
    msg_id = f"cb-{uuid.uuid4().hex[:12]}@contentbridge.io"
    sent_at = datetime.now(UTC).isoformat()
    sender = from_email or settings.smtp_from

    # If SMTP is configured, send via real SMTP
    if settings.smtp_host and settings.smtp_user:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = sender
            msg["To"] = to_email
            msg["Message-ID"] = f"<{msg_id}>"
            msg["Date"] = datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S +0000")

            if cc_emails:
                msg["Cc"] = ", ".join(cc_emails)

            msg.attach(MIMEText(body_text, "plain", "utf-8"))
            if body_html:
                msg.attach(MIMEText(body_html, "html", "utf-8"))

            recipients = [to_email] + (cc_emails or [])

            if settings.smtp_port == 465:
                with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                    server.login(settings.smtp_user, settings.smtp_password)
                    server.sendmail(sender, recipients, msg.as_string())
            else:
                with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                    if settings.smtp_use_tls:
                        server.starttls()
                    server.login(settings.smtp_user, settings.smtp_password)
                    server.sendmail(sender, recipients, msg.as_string())

            log.info("Email dispatched via SMTP to %s (id: %s)", to_email, msg_id)
            return EmailDispatchResult(
                success=True,
                recipient=to_email,
                subject=subject,
                message_id=msg_id,
                sent_at=sent_at,
                delivery_mode="smtp",
                detail=f"Dispatched via SMTP relay to {to_email}",
            )
        except Exception as exc:
            log.exception("SMTP dispatch failed for %s", to_email)
            raise RuntimeError(f"SMTP dispatch failed: {exc}") from exc

    # Simulated local delivery (perfect for hackathon demos and local development)
    log.info(
        "[Simulated Email Dispatch] From: %s | To: %s | Subject: %s | ID: %s",
        sender,
        to_email,
        subject,
        msg_id,
    )
    return EmailDispatchResult(
        success=True,
        recipient=to_email,
        subject=subject,
        message_id=msg_id,
        sent_at=sent_at,
        delivery_mode="simulated",
        detail=f"Successfully queued and delivered to {to_email} (Demo Sandbox Mode)",
    )


async def send_official_email(
    *,
    to_email: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
    cc_emails: list[str] | None = None,
    from_email: str | None = None,
) -> EmailDispatchResult:
    return await anyio.to_thread.run_sync(
        lambda: _send_sync(
            to_email=to_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            cc_emails=cc_emails,
            from_email=from_email,
        )
    )
