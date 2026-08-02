# WebUI 2.0

The redesigned interface keeps the existing Flask and REST architecture while replacing the original fixed desktop map with a responsive dashboard.

## Main improvements

- responsive desktop, tablet and mobile layouts
- dashboard metrics for devices, stored positions, latest observation and selected range
- compact device cards with device type, last-seen information and battery state
- quick ranges for 24 hours, seven days, 30 days and all history
- exact start and end date/time filtering
- dedicated map and chronological timeline views
- improved route rendering and latest-position highlighting
- mobile bottom navigation and slide-out device panel
- integrated Apple authentication status and re-authentication controls
- accessible labels, live regions, visible focus targets and reduced visual clutter

## Technical approach

The redesign intentionally uses the existing Flask application, Leaflet and REST endpoints. It does not introduce a Node.js build pipeline or a separate frontend container. This keeps the Docker image small and preserves straightforward Unraid updates.

The primary files are:

- `templates/index.html` for semantic application structure
- `static/app.css` for the responsive design system
- `static/app.js` for devices, metrics, filters, map rendering and timeline behavior
- `static/auth.css` and `static/auth.js` for the protected Apple authentication workflow

## Data and API compatibility

The interface continues to use:

- `GET /api/devices`
- `GET /api/stats`
- `GET /api/locations`
- `GET /api/auth/status`
- `POST /api/auth/start`
- `POST /api/auth/verify`

No database migration is required.

## UX principles

1. Status before detail: key system and data information is visible without interacting with the map.
2. Progressive disclosure: exact date fields and Apple authentication controls appear only when needed.
3. Mobile parity: all important operations remain available on a phone.
4. Safe defaults: location history remains clearly separated from authentication controls and the existing security guidance remains unchanged.
5. Low operational complexity: the UI is served as static assets by Flask and requires no frontend build step.

## Suggested validation

Before publishing the new image, test:

- desktop widths above 1200 px
- tablet widths around 768–1024 px
- mobile widths around 360–430 px
- an empty database
- one device with one point
- multiple devices with thousands of points
- exact date/time filtering
- map fit and device selection
- timeline-to-map navigation
- the Apple re-authentication modal
- container restart and browser cache refresh
