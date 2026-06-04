"""Configuration management for RU-WiFi."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import configparser
import os

DEFAULT_LOGIN_URL = "http://local.ru.ac.bd/login"
DEFAULT_STATUS_URL = "http://local.ru.ac.bd/status"
DEFAULT_USERNAME_FIELD = "username"
DEFAULT_PASSWORD_FIELD = "password"

DEFAULT_CHECK_INTERVAL_SECONDS = 180
DEFAULT_TIMEOUT_SECONDS = 5
DEFAULT_BACKOFF_SECONDS = 10
DEFAULT_BACKOFF_MAX_SECONDS = 300


@dataclass
class PortalConfig:
    """Captive portal URLs and form field names."""

    login_url: str = DEFAULT_LOGIN_URL
    status_url: str = DEFAULT_STATUS_URL
    username_field: str = DEFAULT_USERNAME_FIELD
    password_field: str = DEFAULT_PASSWORD_FIELD
    extra_fields: dict[str, str] = field(default_factory=dict)


@dataclass
class BehaviorConfig:
    """Behavior tuning values."""

    check_interval_seconds: int = DEFAULT_CHECK_INTERVAL_SECONDS
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    backoff_seconds: int = DEFAULT_BACKOFF_SECONDS
    backoff_max_seconds: int = DEFAULT_BACKOFF_MAX_SECONDS


@dataclass
class CredentialConfig:
    """Credential storage settings."""

    username: str | None = None
    store: str = "keyring"
    credentials_file: Path | None = None


@dataclass
class AppConfig:
    """Full application configuration."""

    portal: PortalConfig = field(default_factory=PortalConfig)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)
    credentials: CredentialConfig = field(default_factory=CredentialConfig)
    log_file: Path | None = None


def _xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def _xdg_state_home() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))


def default_config_path(system: bool) -> Path:
    if system:
        return Path("/etc/ru-wifi/config.ini")
    return _xdg_config_home() / "ru-wifi" / "config.ini"


def default_credentials_path(system: bool) -> Path:
    if system:
        return Path("/etc/ru-wifi/credentials.ini")
    return _xdg_config_home() / "ru-wifi" / "credentials.ini"


def default_log_path() -> Path:
    return _xdg_state_home() / "ru-wifi" / "ru-wifi.log"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def parse_extra_fields(value: str | None) -> dict[str, str]:
    if not value:
        return {}
    fields: dict[str, str] = {}
    for item in value.split(","):
        item = item.strip()
        if not item or "=" not in item:
            continue
        key, field_value = item.split("=", 1)
        fields[key.strip()] = field_value.strip()
    return fields


def format_extra_fields(fields: dict[str, str]) -> str:
    return ",".join(f"{key}={value}" for key, value in fields.items())


def load_config(path: Path, system: bool) -> AppConfig:
    config = configparser.ConfigParser()
    if path.exists():
        config.read(path)

    portal = PortalConfig(
        login_url=config.get("portal", "login_url", fallback=DEFAULT_LOGIN_URL),
        status_url=config.get("portal", "status_url", fallback=DEFAULT_STATUS_URL),
        username_field=config.get("portal", "username_field", fallback=DEFAULT_USERNAME_FIELD),
        password_field=config.get("portal", "password_field", fallback=DEFAULT_PASSWORD_FIELD),
        extra_fields=parse_extra_fields(config.get("portal", "extra_fields", fallback="")),
    )

    behavior = BehaviorConfig(
        check_interval_seconds=config.getint(
            "behavior", "check_interval_seconds", fallback=DEFAULT_CHECK_INTERVAL_SECONDS
        ),
        timeout_seconds=config.getint("behavior", "timeout_seconds", fallback=DEFAULT_TIMEOUT_SECONDS),
        backoff_seconds=config.getint("behavior", "backoff_seconds", fallback=DEFAULT_BACKOFF_SECONDS),
        backoff_max_seconds=config.getint(
            "behavior", "backoff_max_seconds", fallback=DEFAULT_BACKOFF_MAX_SECONDS
        ),
    )

    credentials_file = config.get("credentials", "credentials_file", fallback="")
    credentials = CredentialConfig(
        username=config.get("credentials", "username", fallback=None),
        store=config.get("credentials", "store", fallback="keyring"),
        credentials_file=Path(credentials_file) if credentials_file else None,
    )

    log_file_value = config.get("logging", "log_file", fallback="")
    log_file = Path(log_file_value) if log_file_value else None

    if credentials.credentials_file is None:
        credentials.credentials_file = default_credentials_path(system)

    return AppConfig(portal=portal, behavior=behavior, credentials=credentials, log_file=log_file)


def save_config(path: Path, config: AppConfig) -> None:
    parser = configparser.ConfigParser()
    parser["portal"] = {
        "login_url": config.portal.login_url,
        "status_url": config.portal.status_url,
        "username_field": config.portal.username_field,
        "password_field": config.portal.password_field,
        "extra_fields": format_extra_fields(config.portal.extra_fields),
    }
    parser["behavior"] = {
        "check_interval_seconds": str(config.behavior.check_interval_seconds),
        "timeout_seconds": str(config.behavior.timeout_seconds),
        "backoff_seconds": str(config.behavior.backoff_seconds),
        "backoff_max_seconds": str(config.behavior.backoff_max_seconds),
    }
    parser["credentials"] = {
        "username": config.credentials.username or "",
        "store": config.credentials.store,
        "credentials_file": str(config.credentials.credentials_file or ""),
    }
    parser["logging"] = {
        "log_file": str(config.log_file or ""),
    }

    ensure_parent(path)
    with path.open("w", encoding="utf-8") as handle:
        parser.write(handle)
