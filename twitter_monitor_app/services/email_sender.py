from __future__ import annotations

import smtplib
from email.message import EmailMessage

if __package__ == "twitter_monitor_app.services":
    from ..config.settings import email_issue, get_settings, host_issue, password_issue
else:
    from config.settings import email_issue, get_settings, host_issue, password_issue


class EmailDeliveryError(RuntimeError):
    pass


GMAIL_HOSTS = {"smtp.gmail.com", "smtp.googlemail.com"}


def email_configuration_issues() -> list[str]:
    """Lista cada variable SMTP mal configurada, indicando qué le falta."""
    settings = get_settings()
    checks = [
        ("SMTP_HOST", host_issue(settings.smtp_host)),
        ("SMTP_USERNAME", email_issue(settings.smtp_username)),
        ("SMTP_PASSWORD", password_issue(settings.smtp_password)),
        ("EMAIL_FROM", email_issue(settings.email_from)),
    ]
    return [f"{name} {issue}" for name, issue in checks if issue]


def is_email_delivery_configured() -> bool:
    return not email_configuration_issues()


def _translate_connection_error(exc: Exception) -> str:
    text = str(exc)
    lowered = text.casefold()
    settings = get_settings()

    if "535" in text or "username and password not accepted" in lowered or "badcredentials" in lowered:
        hint = (
            " Gmail no acepta la contraseña de la cuenta: genera una App Password de 16 caracteres "
            "en https://myaccount.google.com/apppasswords y úsala en SMTP_PASSWORD."
            if settings.smtp_host.casefold() in GMAIL_HOSTS
            else " Revisa SMTP_USERNAME y SMTP_PASSWORD."
        )
        return "El servidor rechazó las credenciales." + hint
    if "534" in text or "application-specific password" in lowered:
        return "La cuenta exige una App Password específica de aplicación en SMTP_PASSWORD."
    if "getaddrinfo" in lowered or "name or service not known" in lowered or "nodename nor servname" in lowered:
        return f"No se encontró el servidor '{settings.smtp_host}'. Revisa SMTP_HOST."
    if "connection refused" in lowered:
        return f"El servidor rechazó la conexión en el puerto {settings.smtp_port}. Revisa SMTP_HOST y SMTP_PORT."
    if "timed out" in lowered or "timeout" in lowered:
        return "Se agotó el tiempo de espera al conectar con el servidor SMTP. Revisa SMTP_HOST y SMTP_PORT."
    if "starttls" in lowered or "ssl" in lowered:
        return "Falló el inicio de TLS. Prueba con SMTP_PORT=587, SMTP_USE_TLS=true."
    return f"No se pudo conectar: {text}"


def test_smtp_connection() -> str | None:
    """Intenta conectar y autenticar contra el SMTP.

    Devuelve None si todo funciona, o un mensaje de error con la causa concreta.
    """
    issues = email_configuration_issues()
    if issues:
        return "Configuración incompleta: " + "; ".join(issues) + "."

    settings = get_settings()
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            if settings.smtp_use_tls:
                server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
    except Exception as exc:  # noqa: BLE001
        return _translate_connection_error(exc)
    return None


def send_report_email(
    recipients: list[str],
    subject: str,
    body: str,
    attachment_name: str,
    attachment_bytes: bytes,
    attachment_mime: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
) -> None:
    settings = get_settings()
    issues = email_configuration_issues()
    if issues:
        raise EmailDeliveryError("Configuración SMTP incompleta: " + "; ".join(issues) + ".")
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
        raise EmailDeliveryError(f"No se pudo enviar el correo: {_translate_connection_error(exc)}") from exc
