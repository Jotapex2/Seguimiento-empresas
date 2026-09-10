from __future__ import annotations

import smtplib
from email.message import EmailMessage

from config.settings import get_settings


class EmailDeliveryError(RuntimeError):
    pass


def is_email_delivery_configured() -> bool:
    settings = get_settings()
    required_values = [
        settings.smtp_host,
        settings.smtp_username,
        settings.smtp_password,
        settings.email_from,
    ]
    return all(bool(value.strip()) for value in required_values)


def send_report_email(
    recipients: list[str],
    subject: str,
    body: str,
    attachment_name: str,
    attachment_bytes: bytes,
    attachment_mime: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
) -> None:
    settings = get_settings()
    if not is_email_delivery_configured():
        raise EmailDeliveryError("Falta configurar SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD o EMAIL_FROM en el archivo .env.")
    if not recipients:
        raise EmailDeliveryError("Debes indicar al menos un correo destinatario.")

    maintype, subtype = attachment_mime.split("/", maxsplit=1)
    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(body)
    message.add_attachment(
        attachment_bytes,
        maintype=maintype,
        subtype=subtype,
        filename=attachment_name,
    )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
            if settings.smtp_use_tls:
                server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    except Exception as exc:  # noqa: BLE001
        raise EmailDeliveryError(f"No se pudo enviar el correo: {exc}") from exc
