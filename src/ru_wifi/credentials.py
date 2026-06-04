"""Credential storage helpers."""

from __future__ import annotations

from pathlib import Path
import configparser
import os
import stat
from typing import TextIO

import keyring
from keyring.errors import KeyringError

SERVICE_NAME = "ru-wifi"


def is_root() -> bool:
    if hasattr(os, "geteuid"):
        return os.geteuid() == 0
    return False


def save_password_keyring(username: str, password: str) -> bool:
    try:
        keyring.set_password(SERVICE_NAME, username, password)
    except KeyringError:
        return False
    return True


def load_password_keyring(username: str) -> str | None:
    try:
        return keyring.get_password(SERVICE_NAME, username)
    except KeyringError:
        return None


def _secure_open_for_write(path: Path) -> TextIO:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    return os.fdopen(fd, "w", encoding="utf-8")


def _ensure_permissions(path: Path) -> None:
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def save_password_file(path: Path, password: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _secure_open_for_write(path) as handle:
        parser = configparser.ConfigParser()
        parser["credentials"] = {"password": password}
        parser.write(handle)
    _ensure_permissions(path)


def load_password_file(path: Path) -> str | None:
    if not path.exists():
        return None
    parser = configparser.ConfigParser()
    parser.read(path)
    return parser.get("credentials", "password", fallback=None)


def choose_store(store: str, username: str, password: str, file_path: Path) -> tuple[str, str | None]:
    """Persist the password and return the store type used."""

    if store == "file":
        save_password_file(file_path, password)
        return "file", None

    if save_password_keyring(username, password):
        return "keyring", None

    save_password_file(file_path, password)
    return "file", "Keyring was unavailable; stored password in file."
