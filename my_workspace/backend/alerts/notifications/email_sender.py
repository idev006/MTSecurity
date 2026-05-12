"""SMTP email notification channel."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from alerts.notifications.base import AlertPayload, NotificationChannel, SendResult

logger = logging.getLogger(__name__)


class EmailChannel(NotificationChannel):
    channel_name = "email"

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        from_addr: str,
        to_addrs: list[str],
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._from = from_addr
        self._to = to_addrs

    async def send(self, payload: AlertPayload) -> SendResult:
        subject = f"[{payload.severity.upper()}] {payload.rule_name} — {payload.camera_name}"
        html = f"""
        <h2 style="color:#dc2626">[{payload.severity.upper()}] {payload.rule_name}</h2>
        <table>
          <tr><td><b>Camera</b></td><td>{payload.camera_name}</td></tr>
          <tr><td><b>Behavior</b></td><td>{payload.behavior}</td></tr>
          <tr><td><b>Confidence</b></td><td>{payload.confidence:.0%}</td></tr>
          <tr><td><b>Time</b></td><td>{payload.occurred_at}</td></tr>
        </table>
        {"<img src='" + payload.snapshot_url + "' width='640'/>" if payload.snapshot_url else ""}
        """
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self._from
            msg["To"] = ", ".join(self._to)
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(self._host, self._port) as smtp:
                smtp.starttls()
                smtp.login(self._user, self._password)
                smtp.sendmail(self._from, self._to, msg.as_string())
            return self._result(True)
        except Exception as e:
            logger.error("Email send failed: %s", e)
            return self._result(False, str(e))
