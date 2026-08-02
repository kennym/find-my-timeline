# Release process

This repository uses `pyproject.toml` as the single source of truth for the application version.

## What happens automatically

When a change is merged into `master`, the GitHub Actions workflow:

1. reads the version from `pyproject.toml`
2. builds the Docker image
3. publishes the following GHCR tags
   - `latest`
   - the plain version, for example `0.2.0`
   - the prefixed version, for example `v0.2.0`
   - a commit-specific `sha-*` tag
4. creates a GitHub release named after the version if that release does not already exist

Pull requests build the image without publishing it. The workflow can also be started manually from the GitHub Actions page.

## Preparing a new version

1. Create a release branch from `master`, for example `release-0.3.0`.
2. Update the version in `pyproject.toml`.
3. Add a new section to `CHANGELOG.md` with the release date.
4. Update `<Changes>` and `<Date>` in `templates/find-my-timeline.xml`.
5. Add the new stable image tag as a `<Branch>` entry in the Unraid template.
6. Update documentation for new variables, paths, security behavior or migration steps.
7. Open a pull request and confirm that the Docker build check succeeds.
8. Merge the pull request into `master`.
9. Confirm that the workflow publishes all expected GHCR tags and creates the GitHub release.

## Validation before Community Applications submission

Test the exact public image and template that users will receive.

```bash
docker pull ghcr.io/heckpiet/find-my-timeline-unraid:VERSION
```

Verify at least:

- container starts without privileged mode
- WebUI is reachable through the configured host port
- health status becomes `healthy`
- Apple authentication and 2FA work
- device polling records new locations
- database contents survive container replacement
- Apple session data survives container replacement
- masked template values remain masked
- no secrets appear in application logs
- the raw template, icon, README and screenshots are publicly reachable

Then run `Validate` and `Scan` in the Unraid Community Applications submission portal.

## Rollback

Unraid users can select a previous versioned image tag instead of `latest`, for example:

```text
ghcr.io/heckpiet/find-my-timeline-unraid:0.2.0
```

Persistent data is stored outside the image. Before any rollback, back up both mounted directories:

- `/app/data`
- `/root/.find-my-timeline`

Database schema changes must remain backward-compatible or include an explicit migration and rollback note in `CHANGELOG.md`.

## Package visibility

The GHCR package must remain public so Community Applications and Unraid hosts can pull it without GitHub credentials.
