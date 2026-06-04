"""Command line interface for RU-WiFi."""

from __future__ import annotations

import argparse
import getpass
from pathlib import Path
import sys

from ru_wifi.config import (
    AppConfig,
    default_config_path,
    load_config,
    parse_extra_fields,
    save_config,
)
from ru_wifi.credentials import choose_store, is_root
from ru_wifi.logging_utils import setup_logging
from ru_wifi.portal import PortalClient
from ru_wifi.service import CredentialError, attempt_login_if_needed, run_service


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RU-WiFi captive portal helper.")
    parser.add_argument("--config", help="Path to a custom config file.")
    parser.add_argument(
        "--system", action="store_true", help="Use system config paths (requires sudo)."
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    setup_parser = subparsers.add_parser("setup", help="Store credentials and defaults.")
    setup_parser.add_argument("--login-url", help="Login URL for the portal.")
    setup_parser.add_argument("--status-url", help="Status URL for the portal.")
    setup_parser.add_argument("--username-field", help="Form field name for the username.")
    setup_parser.add_argument("--password-field", help="Form field name for the password.")
    setup_parser.add_argument(
        "--extra-fields",
        help="Extra form fields as key=value pairs separated by commas.",
    )
    setup_parser.add_argument("--interval", type=int, help="Check interval in seconds.")
    setup_parser.add_argument("--timeout", type=int, help="HTTP timeout in seconds.")
    setup_parser.add_argument("--backoff", type=int, help="Initial retry backoff in seconds.")
    setup_parser.add_argument("--backoff-max", type=int, help="Max retry backoff in seconds.")
    setup_parser.add_argument(
        "--store",
        choices=["keyring", "file"],
        help="Force credential storage backend.",
    )
    setup_parser.add_argument("--credentials-file", help="Override credentials file path.")
    setup_parser.add_argument("--log-file", help="Log file path (optional).")
    setup_parser.add_argument("--username", help="Username to save (skip prompt).")

    subparsers.add_parser("login", help="Check and login if needed.")

    subparsers.add_parser("status", help="Report login status.")

    service_parser = subparsers.add_parser("service", help="Run the background service.")
    service_parser.add_argument("--interval", type=int, help="Override check interval.")

    return parser


def resolve_config(args: argparse.Namespace) -> tuple[AppConfig, Path]:
    path = Path(args.config) if args.config else default_config_path(args.system)
    return load_config(path, args.system), path


def apply_setup_overrides(config: AppConfig, args: argparse.Namespace) -> None:
    if args.login_url:
        config.portal.login_url = args.login_url
    if args.status_url:
        config.portal.status_url = args.status_url
    if args.username_field:
        config.portal.username_field = args.username_field
    if args.password_field:
        config.portal.password_field = args.password_field
    if args.extra_fields is not None:
        config.portal.extra_fields = parse_extra_fields(args.extra_fields)
    if args.interval:
        config.behavior.check_interval_seconds = args.interval
    if args.timeout:
        config.behavior.timeout_seconds = args.timeout
    if args.backoff:
        config.behavior.backoff_seconds = args.backoff
    if args.backoff_max:
        config.behavior.backoff_max_seconds = args.backoff_max
    if args.credentials_file:
        config.credentials.credentials_file = Path(args.credentials_file)
    if args.log_file:
        config.log_file = Path(args.log_file)
    if args.store:
        config.credentials.store = args.store


def handle_setup(args: argparse.Namespace) -> int:
    config, path = resolve_config(args)
    apply_setup_overrides(config, args)

    username = args.username or input("Username: ").strip()
    if not username:
        print("Username is required.")
        return 2

    password = getpass.getpass("Password: ")
    if not password:
        print("Password is required.")
        return 2

    if config.credentials.store == "file" and args.system and not is_root():
        print("System credential storage requires sudo.")
        return 2

    store_used, warning = choose_store(
        config.credentials.store, username, password, config.credentials.credentials_file
    )
    config.credentials.username = username
    config.credentials.store = store_used
    save_config(path, config)

    if warning:
        print(warning)
    print(f"Credentials saved using {store_used} storage.")
    print(f"Config saved to {path}.")
    return 0


def handle_status(args: argparse.Namespace) -> int:
    config, _ = resolve_config(args)
    logger = setup_logging(config.log_file)
    client = PortalClient(config.portal, config.behavior.timeout_seconds, logger)
    status = client.check_logged_in()
    print("Logged in." if status.logged_in else "Login required.")
    print(status.detail)
    return 0 if status.logged_in else 1


def handle_login(args: argparse.Namespace) -> int:
    config, _ = resolve_config(args)
    logger = setup_logging(config.log_file)
    try:
        success = attempt_login_if_needed(config, logger)
    except CredentialError as exc:
        print(exc)
        return 2
    return 0 if success else 1


def handle_service(args: argparse.Namespace) -> int:
    config, _ = resolve_config(args)
    logger = setup_logging(config.log_file)
    try:
        run_service(config, logger, args.interval)
    except CredentialError as exc:
        logger.error("%s", exc)
        return 2
    except KeyboardInterrupt:
        logger.info("Service stopped.")
    return 0


def ru_wifi() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "setup":
        sys.exit(handle_setup(args))
    if args.command == "login":
        sys.exit(handle_login(args))
    if args.command == "status":
        sys.exit(handle_status(args))
    if args.command == "service":
        sys.exit(handle_service(args))


if __name__ == "__main__":
    ru_wifi()
