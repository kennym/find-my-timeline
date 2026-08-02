"""iCloud authentication module with CLI and web-based 2FA support."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

from pyicloud import PyiCloudService
from pyicloud.exceptions import PyiCloudFailedLoginException


class ICloudAuth:
    """Handle iCloud authentication including interactive and web-based 2FA."""

    def __init__(self, username: str, password: str | None = None):
        self.username = username
        self.password = password
        self.api: PyiCloudService | None = None
        self._cookie_dir = Path.home() / ".find-my-timeline"
        self._cookie_dir.mkdir(exist_ok=True)
        self._metadata_file = self._cookie_dir / "auth-metadata.json"
        self._lock = RLock()

    def _session_paths(self) -> tuple[Path, Path]:
        username_clean = self.username.replace("@", "").replace(".", "")
        return (
            self._cookie_dir / f"{username_clean}.session",
            self._cookie_dir / f"{username_clean}.cookiejar",
        )

    def has_valid_session(self) -> bool:
        """Check whether the expected session files exist without contacting Apple."""
        session_file, cookie_file = self._session_paths()
        return session_file.exists() and cookie_file.exists()

    def _create_service(self, password: str | None = None) -> PyiCloudService:
        try:
            return PyiCloudService(
                self.username,
                password if password is not None else self.password,
                cookie_directory=str(self._cookie_dir),
            )
        except PyiCloudFailedLoginException as exc:
            error_msg = str(exc)
            if "503" in error_msg or "srp" in error_msg.lower():
                raise AuthenticationError(
                    "Apple rejected the login request. Authenticate from a trusted local "
                    "network or use the CLI and copy the session files into the container."
                ) from exc
            raise AuthenticationError("Apple ID authentication failed") from exc

    def authenticate(self, allow_2fa: bool = True) -> PyiCloudService:
        """Authenticate with iCloud and optionally complete 2FA interactively."""
        with self._lock:
            self.api = self._create_service()
            if self.api.requires_2fa:
                if not allow_2fa:
                    raise AuthenticationError("Two-factor authentication is required")
                self._handle_2fa()
            elif self.api.requires_2sa:
                if not allow_2fa:
                    raise AuthenticationError("Two-step authentication is required")
                self._handle_2sa()
            self.record_successful_authentication()
            return self.api

    def begin_web_authentication(self, password: str | None = None) -> dict:
        """Start a browser-based authentication flow without retaining the password."""
        with self._lock:
            self.api = self._create_service(password)
            password = None
            if self.api.requires_2sa:
                raise AuthenticationError(
                    "Legacy two-step authentication is not supported in the WebUI. Use the CLI."
                )
            if self.api.requires_2fa:
                request_code = getattr(self.api, "request_2fa_code", None)
                if callable(request_code):
                    request_code()
                return {"requires_2fa": True, "status": "waiting_for_code"}
            self.record_successful_authentication()
            return {"requires_2fa": False, "status": "authenticated"}

    def complete_web_2fa(self, code: str) -> None:
        """Validate a 2FA code for a previously started web flow."""
        if not code or not code.isdigit() or len(code) not in {6, 8}:
            raise AuthenticationError("Enter the verification code shown on your Apple device")
        with self._lock:
            if not self.api or not self.api.requires_2fa:
                raise AuthenticationError("No active two-factor authentication request")
            if not self.api.validate_2fa_code(code):
                raise AuthenticationError("The verification code was rejected")
            if not self.api.is_trusted_session and not self.api.trust_session():
                raise AuthenticationError("Apple accepted the code but did not trust the session")
            self.record_successful_authentication()

    def record_successful_authentication(self) -> None:
        payload = {
            "username": self.username,
            "authenticated_at": datetime.now(timezone.utc).isoformat(),
        }
        temporary = self._metadata_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(self._metadata_file)

    def authentication_metadata(self, lifetime_days: int = 90) -> dict:
        """Return non-secret session metadata and an estimated expiry countdown."""
        result = {
            "configured": bool(self.username),
            "session_files_present": self.has_valid_session(),
            "authenticated_at": None,
            "estimated_expires_at": None,
            "remaining_days": None,
            "state": "unknown",
        }
        if not self._metadata_file.exists():
            result["state"] = "session_present" if result["session_files_present"] else "missing"
            return result
        try:
            data = json.loads(self._metadata_file.read_text(encoding="utf-8"))
            authenticated_at = datetime.fromisoformat(data["authenticated_at"])
            if authenticated_at.tzinfo is None:
                authenticated_at = authenticated_at.replace(tzinfo=timezone.utc)
            expires_at = authenticated_at.timestamp() + (lifetime_days * 86400)
            now = datetime.now(timezone.utc).timestamp()
            remaining = max(0, int((expires_at - now + 86399) // 86400))
            result.update(
                authenticated_at=authenticated_at.isoformat(),
                estimated_expires_at=datetime.fromtimestamp(expires_at, timezone.utc).isoformat(),
                remaining_days=remaining,
                state="expired" if expires_at <= now else ("warning" if remaining <= 14 else "valid"),
            )
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            result["state"] = "session_present" if result["session_files_present"] else "missing"
        return result

    def _handle_2fa(self) -> None:
        print("Two-factor authentication required.")
        request_code = getattr(self.api, "request_2fa_code", None)
        if callable(request_code):
            request_code()
        code = input("Enter the 2FA code sent to your trusted devices: ").strip()
        self.complete_web_2fa(code)

    def _handle_2sa(self) -> None:
        print("Two-step authentication required.")
        devices = self.api.trusted_devices
        for index, device in enumerate(devices):
            print(f"  {index}: {device.get('deviceName', f'Device {index}')}" )
        device = devices[int(input("Select device: ").strip())]
        if not self.api.send_verification_code(device):
            raise AuthenticationError("Failed to send verification code")
        code = input("Enter the verification code: ").strip()
        if not self.api.validate_verification_code(device, code):
            raise AuthenticationError("Invalid verification code")

    def get_devices(self) -> list[dict]:
        if not self.api:
            raise AuthenticationError("Not authenticated. Call authenticate() first.")
        devices = []
        for device in self.api.devices:
            data = device.data
            devices.append({
                "id": data.get("id", "unknown"),
                "name": data.get("name", "Unknown Device"),
                "device_display_name": data.get("deviceDisplayName", "Unknown"),
                "device_class": data.get("deviceClass", "unknown"),
                "battery_level": data.get("batteryLevel"),
                "battery_status": data.get("batteryStatus"),
                "location": device.location,
            })
        return devices


class AuthenticationError(Exception):
    """Raised when authentication fails."""
