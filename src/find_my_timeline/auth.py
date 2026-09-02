"""iCloud authentication module with 2FA support."""
from pathlib import Path

from pyicloud import PyiCloudService
from pyicloud.exceptions import PyiCloudFailedLoginException


class ICloudAuth:
    """Handles iCloud authentication including 2FA."""

    def __init__(self, username: str, password: str | None = None):
        self.username = username
        self.password = password
        self.api: PyiCloudService | None = None
        self._cookie_dir = Path.home() / ".find-my-timeline"
        self._cookie_dir.mkdir(exist_ok=True)

    def has_valid_session(self) -> bool:
        """Check if valid session cookies exist without triggering 2FA."""
        username_clean = self.username.replace("@", "").replace(".", "")
        session_file = self._cookie_dir / f"{username_clean}.session"
        cookie_file = self._cookie_dir / f"{username_clean}.cookiejar"
        return session_file.exists() and cookie_file.exists()

    def authenticate(self, allow_2fa: bool = True) -> PyiCloudService:
        """Authenticate with iCloud and return the API instance."""
        try:
            self.api = PyiCloudService(
                self.username,
                self.password,
                cookie_directory=str(self._cookie_dir),
            )
        except PyiCloudFailedLoginException as exc:
            error_msg = str(exc)
            if "503" in error_msg or "srp" in error_msg.lower():
                raise AuthenticationError(
                    f"Failed to login to iCloud: {exc}\n\n"
                    "This often happens when Apple blocks the server's IP address.\n"
                    "To fix this, authenticate locally and copy session files:\n"
                    "  1. Run 'find-my-timeline auth' on your local machine\n"
                    "  2. Copy ~/.find-my-timeline/* to the Docker volume\n"
                    "  3. Restart the container"
                ) from exc
            raise AuthenticationError(f"Failed to login to iCloud: {exc}") from exc

        if self.api.requires_2fa:
            if not allow_2fa:
                raise AuthenticationError(
                    "2FA required but not allowed in non-interactive mode. "
                    "Run 'find-my-timeline auth' interactively first to create a session."
                )
            self._handle_2fa()
        elif self.api.requires_2sa:
            if not allow_2fa:
                raise AuthenticationError(
                    "2SA required but not allowed in non-interactive mode. "
                    "Run 'find-my-timeline auth' interactively first to create a session."
                )
            self._handle_2sa()

        return self.api

    def _handle_2fa(self) -> None:
        """Handle two-factor authentication."""
        print("Two-factor authentication required.")
        print("Requesting a new verification code from Apple...")
        self.api.request_2fa_code()
        code = input("Enter the 2FA code sent to your trusted devices: ").strip()

        if not self.api.validate_2fa_code(code):
            raise AuthenticationError("Invalid 2FA code")

        print("2FA authentication successful!")

        if not self.api.is_trusted_session:
            print("Session is not trusted. Requesting trust...")
            if self.api.trust_session():
                print("Session trusted successfully.")
            else:
                print(
                    "Warning: Failed to trust session. "
                    "You may need to re-authenticate sooner."
                )

    def _handle_2sa(self) -> None:
        """Handle two-step authentication for legacy Apple accounts."""
        print("Two-step authentication required.")
        devices = self.api.trusted_devices

        print("Trusted devices:")
        for index, device in enumerate(devices):
            name = device.get("deviceName", f"Device {index}")
            print(f"  {index}: {name}")

        device_index = int(input("Select device to receive verification code: ").strip())
        device = devices[device_index]

        if not self.api.send_verification_code(device):
            raise AuthenticationError("Failed to send verification code")

        code = input("Enter the verification code: ").strip()

        if not self.api.validate_verification_code(device, code):
            raise AuthenticationError("Invalid verification code")

        print("2SA authentication successful!")

    def get_devices(self) -> list[dict]:
        """Get all devices from the Find My iPhone service."""
        if not self.api:
            raise AuthenticationError("Not authenticated. Call authenticate() first.")

        devices = []
        for device in self.api.devices:
            location = device.location
            data = device.data

            devices.append(
                {
                    "id": data.get("id", "unknown"),
                    "name": data.get("name", "Unknown Device"),
                    "device_display_name": data.get("deviceDisplayName", "Unknown"),
                    "device_class": data.get("deviceClass", "unknown"),
                    "battery_level": data.get("batteryLevel"),
                    "battery_status": data.get("batteryStatus"),
                    "location": location,
                }
            )

        return devices


class AuthenticationError(Exception):
    """Raised when authentication fails."""
