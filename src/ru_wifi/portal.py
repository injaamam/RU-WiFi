"""Portal communication helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

from ru_wifi.config import PortalConfig


@dataclass
class PortalStatus:
    logged_in: bool
    detail: str


class PortalClient:
    """Handles requests to the RU captive portal."""

    def __init__(self, portal: PortalConfig, timeout: int, logger: logging.Logger):
        self.portal = portal
        self.timeout = timeout
        self.session = requests.Session()
        self.logger = logger

    def _get(self, url: str) -> requests.Response:
        return self.session.get(url, timeout=self.timeout, allow_redirects=True)

    def _post(self, url: str, data: dict[str, str]) -> requests.Response:
        return self.session.post(url, data=data, timeout=self.timeout, allow_redirects=True)

    def _response_indicates_logged_in(self, response: requests.Response) -> bool:
        if "/status" in response.url:
            return True
        if "/login" in response.url:
            return False
        content = response.text.lower()
        return "logout" in content or "status" in content

    def check_logged_in(self) -> PortalStatus:
        """Check whether the portal reports an active session."""

        try:
            status_response = self._get(self.portal.status_url)
            if self._response_indicates_logged_in(status_response):
                return PortalStatus(True, "Status URL indicates an active session.")
        except requests.RequestException as exc:
            self.logger.debug("Status check failed: %s", exc)

        try:
            login_response = self._get(self.portal.login_url)
            if self._response_indicates_logged_in(login_response):
                return PortalStatus(True, "Login URL redirected to status.")
            return PortalStatus(False, "Login URL still shows the login form.")
        except requests.RequestException as exc:
            self.logger.warning("Login check failed: %s", exc)
            return PortalStatus(False, "Login check failed.")

    def login(self, username: str, password: str) -> PortalStatus:
        """Attempt to login to the portal."""

        payload = {
            self.portal.username_field: username,
            self.portal.password_field: password,
            **self.portal.extra_fields,
        }
        try:
            response = self._post(self.portal.login_url, payload)
            if self._response_indicates_logged_in(response):
                return PortalStatus(True, "Login POST redirected to status.")
        except requests.RequestException as exc:
            self.logger.warning("Login POST failed: %s", exc)
            return PortalStatus(False, "Login POST failed.")

        # Final verification using the status URL.
        return self.check_logged_in()
