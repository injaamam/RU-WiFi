"""Service loop for RU-WiFi."""

from __future__ import annotations

import logging
import time

from ru_wifi.config import AppConfig
from ru_wifi.credentials import load_password_file, load_password_keyring
from ru_wifi.portal import PortalClient


class CredentialError(RuntimeError):
    """Raised when credentials are missing."""


def load_credentials(config: AppConfig) -> tuple[str, str]:
    username = config.credentials.username
    if not username:
        raise CredentialError("Username is not configured. Run 'ru-wifi setup' first.")

    password = None
    if config.credentials.store == "keyring":
        password = load_password_keyring(username)

    if not password and config.credentials.credentials_file:
        password = load_password_file(config.credentials.credentials_file)

    if not password:
        raise CredentialError("Password not found. Run 'ru-wifi setup' to store it.")

    return username, password


def attempt_login_if_needed(config: AppConfig, logger: logging.Logger) -> bool:
    """Check login state and authenticate only when required."""

    username, password = load_credentials(config)
    client = PortalClient(config.portal, config.behavior.timeout_seconds, logger)

    status = client.check_logged_in()
    if status.logged_in:
        logger.info("Already logged in: %s", status.detail)
        return True

    logger.info("Login required: %s", status.detail)
    login_status = client.login(username, password)
    if login_status.logged_in:
        logger.info("Login succeeded: %s", login_status.detail)
        return True

    logger.warning("Login failed: %s", login_status.detail)
    return False


def run_service(config: AppConfig, logger: logging.Logger, interval_override: int | None = None) -> None:
    """Run the background loop that keeps the session alive."""

    interval = interval_override or config.behavior.check_interval_seconds
    backoff = config.behavior.backoff_seconds
    max_backoff = config.behavior.backoff_max_seconds

    while True:
        success = attempt_login_if_needed(config, logger)
        if success:
            backoff = config.behavior.backoff_seconds
            sleep_for = interval
        else:
            sleep_for = min(backoff, max_backoff)
            backoff = min(backoff * 2, max_backoff)

        logger.info("Next check in %s seconds.", sleep_for)
        time.sleep(sleep_for)
