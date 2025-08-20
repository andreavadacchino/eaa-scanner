from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from typing import Optional


class SmtpConfig:
    def __init__(self) -> None:
        self.host = os.getenv("SMTP_HOST", "")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.user = os.getenv("SMTP_USER", "")
        self.password = os.getenv("SMTP_PASS", "")
        self.sender = os.getenv("SMTP_FROM", self.user or "")
        self.use_tls = os.getenv("SMTP_TLS", "true").lower() in {"1", "true", "yes", "on"}

    def is_configured(self) -> bool:
        return bool(self.host and self.sender)


def send_pdf(pdf_path: Path, to_email: str, subject: str, body: str) -> tuple[bool, str]:
    cfg = SmtpConfig()
    if not to_email:
        return False, "recipient missing"
    if not pdf_path.exists():
        return False, "pdf not found"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg.sender or "no-reply@example.com"
    msg["To"] = to_email
    msg.set_content(body)

    data = pdf_path.read_bytes()
    msg.add_attachment(data, maintype="application", subtype="pdf", filename=pdf_path.name)

    if not cfg.is_configured():
        # fallback: write .eml next to pdf
        eml = pdf_path.with_suffix(".eml")
        eml.write_bytes(msg.as_bytes())
        return False, f"smtp not configured; wrote {eml.name}"

    try:
        if cfg.use_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP(cfg.host, cfg.port) as server:
                server.starttls(context=context)
                if cfg.user and cfg.password:
                    server.login(cfg.user, cfg.password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(cfg.host, cfg.port) as server:
                if cfg.user and cfg.password:
                    server.login(cfg.user, cfg.password)
                server.send_message(msg)
        return True, "sent"
    except Exception as e:
        return False, str(e)

