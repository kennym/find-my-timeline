# Changelog

All notable changes to this Unraid-focused fork are documented in this file.

The project follows Semantic Versioning. Docker images are published with `latest`, the plain version such as `0.2.0`, the prefixed version such as `v0.2.0`, and a commit-specific `sha-*` tag.

## [0.2.0] - 2026-07-27

### Added

- Unraid Community Applications template with persistent database and Apple session paths.
- Public Docker image publishing through GitHub Container Registry.
- Responsive WebUI 2.0 with desktop and mobile navigation.
- Device cards, route map, exact date and time filtering, status metrics and chronological timeline.
- Apple session status and estimated re-authentication countdown.
- Optional protected browser-based Apple 2FA re-authentication.
- Configurable administrator password for authentication actions.
- Docker health check and OCI image metadata.
- Versioned Docker image tags derived from `pyproject.toml`.
- Automated GitHub release creation for new versions merged into `master`.
- Community Applications screenshots and selectable stable image tags.

### Fixed

- Apple 2FA now explicitly requests a fresh verification code before validating it.
- CLI version output now comes from installed package metadata and no longer needs a separate hard-coded version update.

### Security

- Apple ID passwords and verification codes used by the WebUI authentication flow are not written to SQLite or authentication metadata.
- Sensitive password fields are masked in the Unraid template.
- Security response headers and expiring in-memory authentication flows are documented and enabled.
- The documentation clearly warns against exposing location history directly to the internet.

### Validation

The release candidate was tested successfully on Unraid OS 7.3.2 with:

- public GHCR image pull
- installation through the Unraid Docker template
- persistent SQLite database storage
- persistent Apple session and cookie storage
- Apple two-factor authentication
- device discovery and location polling
- WebUI access on port 5000
- container restart and data persistence
- Docker health check

## [0.1.0] - 2026-07-24

### Added

- Initial fork of `kennym/find-my-timeline`.
- Basic Docker packaging, SQLite location history, polling service and map-based WebUI.

[0.2.0]: https://github.com/heckpiet/find-my-timeline-unraid/releases/tag/v0.2.0
[0.1.0]: https://github.com/heckpiet/find-my-timeline-unraid/commits/master
