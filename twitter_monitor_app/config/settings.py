import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv()

MIN_SECRET_LENGTH = 8

PLACEHOLDER_VALUES = {
    "pega_aqui_tu_api_key",
    "pega_aqui_tu_password_smtp",
    "tu_api_key_aqui",
    "tu_api_key_serper_aqui",
    "tu_google_api_key_aqui",
    "tu_google_search_engine_id_aqui",
    "tu_searchapi_key_aqui",
    "your_api_key_here",
    "your_deepseek_api_key_here",
    "your_smtp_password",
    "smtp.example.com",
    "usuario@example.com",
}


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or "").strip()


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


def secret_issue(value: str, min_length: int = MIN_SECRET_LENGTH) -> str:
    """Describe qué le falta a una credencial, o devuelve "" si parece válida."""
    cleaned = (value or "").strip()
    if not cleaned:
        return "está vacía"
    if cleaned.casefold() in PLACEHOLDER_VALUES:
        return "conserva el valor de ejemplo"
    if len(cleaned) < min_length:
        return f"parece incompleta ({len(cleaned)} caracteres)"
    return ""


def is_secret_configured(value: str, min_length: int = MIN_SECRET_LENGTH) -> bool:
    return not secret_issue(value, min_length)


def host_issue(value: str) -> str:
    """Valida un nombre de servidor (SMTP_HOST)."""
    cleaned = (value or "").strip()
    if not cleaned:
        return "está vacío"
    if cleaned.casefold() in PLACEHOLDER_VALUES:
        return "conserva el valor de ejemplo"
    if "." not in cleaned:
        return "no parece un servidor válido"
    return ""


def email_issue(value: str) -> str:
    """Valida una dirección de correo (SMTP_USERNAME, EMAIL_FROM)."""
    cleaned = (value or "").strip()
    if not cleaned:
        return "está vacío"
    if cleaned.casefold() in PLACEHOLDER_VALUES:
        return "conserva el valor de ejemplo"
    if "@" not in cleaned:
        return "no parece un correo válido"
    return ""


def password_issue(value: str) -> str:
    """Valida una contraseña SMTP, avisando por espacios internos."""
    issue = secret_issue(value, MIN_SECRET_LENGTH)
    if issue:
        return issue
    if any(character.isspace() for character in value.strip()):
        return "contiene espacios internos"
    return ""


@dataclass(frozen=True)
class AppConfig:
    app_name: str = "Monitoreo Sectorial X/Twitter Chile"
    api_key: str = _env("TWITTERAPI_IO_KEY")
    base_url: str = _env("BASE_URL", "https://api.twitterapi.io")
    default_limit: int = 10000
    max_limit: int = 10000
    default_google_results_per_keyword: int = 1000
    max_google_results_per_keyword: int = 1000
    request_timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 1.5
    page_size: int = 20
    default_query_type: str = "Latest"
    default_cache_ttl_hours: int = 6
    smtp_host: str = _env("SMTP_HOST")
    smtp_port: int = _env_int("SMTP_PORT", 587)
    smtp_username: str = _env("SMTP_USERNAME")
    smtp_password: str = _env("SMTP_PASSWORD")
    smtp_use_tls: bool = _env("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes", "on"}
    email_from: str = _env("EMAIL_FROM")
    deepseek_api_key: str = _env("DEEPSEEK_API_KEY")
    deepseek_api_url: str = _env("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
    deepseek_model: str = _env("DEEPSEEK_MODEL", "deepseek-chat")

    @property
    def api_key_issue(self) -> str:
        return secret_issue(self.api_key)

    @property
    def api_key_configured(self) -> bool:
        return not self.api_key_issue

    @property
    def deepseek_issue(self) -> str:
        return secret_issue(self.deepseek_api_key)

    @property
    def deepseek_configured(self) -> bool:
        return not self.deepseek_issue
    runtime_dir: Path = Path(__file__).resolve().parents[1] / "data" / "runtime"
    supported_languages: List[str] = field(default_factory=lambda: ["es"])
    priority_people_boost: float = 10.0
    context_terms: List[str] = field(
        default_factory=lambda: [
            "chile",
            "santiago",
            "valparaiso",
            "biobio",
            "atacama",
            "antofagasta",
            "apr",
            "superintendencia",
            "siss",
            "mop",
            "dga",
        ]
    )


def get_settings() -> AppConfig:
    return AppConfig()
