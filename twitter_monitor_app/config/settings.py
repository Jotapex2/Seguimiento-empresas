import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    app_name: str = "Monitoreo Sectorial X/Twitter Chile"
    api_key: str = os.getenv("TWITTERAPI_IO_KEY", "")
    base_url: str = os.getenv("BASE_URL", "https://api.twitterapi.io")
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
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_use_tls: bool = os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "on"}
    email_from: str = os.getenv("EMAIL_FROM", "")
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_api_url: str = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
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
