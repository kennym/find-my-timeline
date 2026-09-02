# Find My Timeline for Unraid

Unofficial Unraid-ready fork of [kennym/find-my-timeline](https://github.com/kennym/find-my-timeline).

Find My Timeline polls devices available through Apple's Find My service at configurable intervals and stores their historical positions in a local SQLite database. The WebUI displays devices, routes and timelines on an interactive map.

> This project is not affiliated with or endorsed by Apple or Lime Technology.

![Preview](preview.png)
![Preview Detail](preview2.png)
![Preview Timeline](preview3.png)

## Unraid installation

Install the app from Community Applications once published, or use the template directly:

```text
https://raw.githubusercontent.com/heckpiet/find-my-timeline-unraid/master/templates/find-my-timeline.xml
```

The Docker image is published through GitHub Container Registry:

```text
ghcr.io/heckpiet/find-my-timeline-unraid:latest
```

### First authentication

1. Install the container and set `ICLOUD_USERNAME` to your Apple ID email address.
2. Keep both persistent paths enabled:
   - `/app/data`
   - `/root/.find-my-timeline`
3. Open the container console in Unraid.
4. Run:

```bash
find-my-timeline auth
```

5. Enter your Apple ID password and the newly requested two-factor authentication code.
6. Restart the container.

The Apple session is stored in the persistent session path. Re-run the command when Apple expires the session.

## Configuration

| Variable | Default | Description |
|---|---:|---|
| `ICLOUD_USERNAME` | — | Apple ID email address |
| `ICLOUD_PASSWORD` | unset | Optional; entering the password interactively is recommended |
| `POLL_MIN_INTERVAL` | `7` | Minimum interval between requests in minutes |
| `POLL_MAX_INTERVAL` | `10` | Maximum interval between requests in minutes |
| `DATABASE_PATH` | `/app/data/locations.db` | SQLite database path |
| `WEB_HOST` | `0.0.0.0` | Web server binding inside the container |
| `WEB_PORT` | `5000` | Internal WebUI port |
| `TZ` | `Europe/Berlin` in the Unraid template | Container timezone |

## Persistent data

| Container path | Purpose |
|---|---|
| `/app/data` | SQLite database containing device and location history |
| `/root/.find-my-timeline` | Apple session and cookie files |

Back up both paths, especially `/app/data`.

## Security notice

The current WebUI does not provide its own authentication. Do not expose port 5000 directly to the internet. Access it through your trusted local network, a VPN such as WireGuard or Tailscale, or a reverse proxy with authentication.

Location data is sensitive personal information. Protect the appdata directory and its backups accordingly.

## Docker usage outside Unraid

```bash
mkdir -p data session

docker run -d \
  --name find-my-timeline \
  --restart unless-stopped \
  -p 5000:5000 \
  -e ICLOUD_USERNAME=your-apple-id@example.com \
  -e POLL_MIN_INTERVAL=7 \
  -e POLL_MAX_INTERVAL=10 \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/session:/root/.find-my-timeline" \
  ghcr.io/heckpiet/find-my-timeline-unraid:latest
```

Authenticate interactively afterward:

```bash
docker exec -it find-my-timeline find-my-timeline auth
docker restart find-my-timeline
```

## Commands

| Command | Description |
|---|---|
| `find-my-timeline auth` | Authenticate with iCloud and handle 2FA |
| `find-my-timeline poll` | Start location polling only |
| `find-my-timeline web` | Start the WebUI only |
| `find-my-timeline start` | Start polling and the WebUI |
| `find-my-timeline stats` | Show database statistics |
| `find-my-timeline devices` | List tracked devices |

## Community Applications publishing checklist

1. Merge the Unraid preparation branch into `master`.
2. Confirm the GitHub Actions Docker workflow succeeds.
3. Open the package settings for `ghcr.io/heckpiet/find-my-timeline-unraid` and set the package visibility to **Public**.
4. Pull and test `ghcr.io/heckpiet/find-my-timeline-unraid:latest` on Unraid.
5. Validate and scan the repository at the Unraid Community Applications submission portal.
6. Submit the repository for review once all checks pass.

## License and attribution

The application remains licensed under the MIT License. Original copyright notices and attribution are retained in `LICENSE`.
