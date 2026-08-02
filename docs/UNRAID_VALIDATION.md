# Unraid validation record

## Release candidate

- Application version: `0.2.0`
- Validation date: 2026-07-27
- Unraid OS: 7.3.2
- Container image: `ghcr.io/heckpiet/find-my-timeline-unraid:latest`
- Network mode: bridge
- WebUI container port: 5000

## Persistent paths

| Purpose | Container path | Unraid host path |
|---|---|---|
| SQLite database | `/app/data` | `/mnt/user/appdata/find-my-timeline/data` |
| Apple session and cookies | `/root/.find-my-timeline` | `/mnt/user/appdata/find-my-timeline/session` |

## Tests completed

| Test | Result |
|---|---|
| Pull public image from GHCR without credentials | Passed |
| Create container through the Unraid template | Passed |
| Start without privileged mode | Passed |
| Reach the WebUI through the configured host port | Passed |
| Authenticate with Apple ID and a newly requested 2FA code | Passed |
| Discover devices available through Apple Find My | Passed |
| Poll and store device location records | Passed |
| Display devices and historical data in the WebUI | Passed |
| Restart container without losing SQLite data | Passed |
| Recreate container without losing Apple session data | Passed |
| Docker health check reaches `healthy` | Passed |
| Mask administrator and optional Apple password fields | Passed |

## Security observations

- The WebUI contains sensitive location history and was tested only on a trusted private network.
- Port 5000 must not be forwarded directly to the public internet.
- Remote access should use a VPN or an authenticated HTTPS reverse proxy.
- The Apple session directory and database directory must be included in protected backups.
- Screenshots, logs and issue reports must redact Apple IDs, verification codes, device identifiers and location data.

## Regression checks for future releases

Future releases should repeat the tests above and additionally verify any new environment variables, database migrations, authentication behavior and rollback instructions.
