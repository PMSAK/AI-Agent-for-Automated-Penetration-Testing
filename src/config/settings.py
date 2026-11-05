"""Configuration loading from environment variables (.env supported)."""
import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str
    database_path: Path
    scanner_output_dir: Path
    reports_dir: Path
    log_level: str
    authorized_targets: tuple[str, ...] = ()
    excluded_targets: tuple[str, ...] = ()
    allowed_operations: tuple[str, ...] = ()
    nmap_path: str = ""
    nmap_timeout_seconds: int = 300
    zap_api_url: str = "http://127.0.0.1:8090"
    zap_api_key: str = ""
    zap_timeout_seconds: int = 300

    @property
    def api_key_configured(self) -> bool:
        return bool(self.openai_api_key)

    def __repr__(self) -> str:  # never expose the key
        return f"Settings(api_key_configured={self.api_key_configured}, model={self.openai_model!r})"


def _positive_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, ""))
    except ValueError:
        return default
    return value if value > 0 else default


def _csv(name: str) -> tuple[str, ...]:
    return tuple(p.strip() for p in os.getenv(name, "").split(",") if p.strip())


def load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        database_path=PROJECT_ROOT / os.getenv("DATABASE_PATH", "data/database/vapt.db"),
        scanner_output_dir=PROJECT_ROOT / os.getenv("SCANNER_OUTPUT_DIR", "data/scanner_outputs"),
        reports_dir=PROJECT_ROOT / os.getenv("REPORTS_DIR", "reports"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        authorized_targets=_csv("AUTHORIZED_TARGETS"),
        excluded_targets=_csv("EXCLUDED_TARGETS"),
        allowed_operations=_csv("ALLOWED_OPERATIONS"),
        nmap_path=os.getenv("NMAP_PATH", "").strip(),
        nmap_timeout_seconds=_positive_int("NMAP_TIMEOUT_SECONDS", 300),
        zap_api_url=os.getenv("ZAP_API_URL", "http://127.0.0.1:8090").strip(),
        zap_api_key=os.getenv("ZAP_API_KEY", "").strip(),
        zap_timeout_seconds=_positive_int("ZAP_TIMEOUT_SECONDS", 300),
    )


def check_scanner_availability() -> dict[str, bool]:
    """Only checks whether executables are on PATH; never runs a scan."""
    return {name: shutil.which(name) is not None for name in ("nmap", "nikto")}


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

