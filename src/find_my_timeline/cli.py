"""Command-line interface for Find My Timeline."""

import logging
import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from threading import Thread

import click
from dotenv import load_dotenv

from .auth import AuthenticationError, ICloudAuth
from .database import LocationDatabase
from .poller import LocationPoller
from .web import create_app

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

try:
    APP_VERSION = version("find-my-timeline")
except PackageNotFoundError:
    APP_VERSION = "development"


def get_config():
    """Get configuration from environment variables."""
    return {
        "username": os.getenv("ICLOUD_USERNAME"),
        "password": os.getenv("ICLOUD_PASSWORD"),
        "min_interval": int(os.getenv("POLL_MIN_INTERVAL", "7")),
        "max_interval": int(os.getenv("POLL_MAX_INTERVAL", "10")),
        "db_path": os.getenv("DATABASE_PATH", "./data/locations.db"),
        "web_host": os.getenv("WEB_HOST", "127.0.0.1"),
        "web_port": int(os.getenv("WEB_PORT", "5000")),
    }


@click.group()
@click.version_option(version=APP_VERSION)
def main():
    """Find My Timeline - Track your Apple device locations over time."""


@main.command()
@click.option("--username", "-u", help="iCloud username (Apple ID)")
@click.option("--password", "-p", help="iCloud password", hide_input=True)
def auth(username, password):
    """Authenticate with iCloud and store the session."""
    config = get_config()
    username = username or config["username"] or click.prompt("Enter your Apple ID")
    password = password or config["password"] or click.prompt("Enter your password", hide_input=True)
    click.echo(f"Authenticating as {username}...")
    try:
        handler = ICloudAuth(username, password)
        handler.authenticate()
        click.echo("Authentication successful. Session and metadata saved.")
        devices = handler.get_devices()
        click.echo(f"Found {len(devices)} device(s):")
        for device in devices:
            location_status = "Has location" if device.get("location") else "No location"
            click.echo(f"  - {device['name']} ({device['device_display_name']}) - {location_status}")
    except AuthenticationError as exc:
        click.echo(f"Authentication failed: {exc}", err=True)
        sys.exit(1)


@main.command()
@click.option("--username", "-u", help="iCloud username (Apple ID)")
@click.option("--password", "-p", help="iCloud password")
@click.option("--min-interval", type=int, help="Minimum polling interval in minutes")
@click.option("--max-interval", type=int, help="Maximum polling interval in minutes")
def poll(username, password, min_interval, max_interval):
    """Start the location polling service."""
    config = get_config()
    username = username or config["username"]
    password = password or config["password"]
    min_interval = min_interval or config["min_interval"]
    max_interval = max_interval or config["max_interval"]
    if not username:
        click.echo("Error: ICLOUD_USERNAME is required", err=True)
        sys.exit(1)
    handler = ICloudAuth(username, password)
    database = LocationDatabase(config["db_path"])
    poller = LocationPoller(handler, database, min_interval, max_interval)
    poller.on_poll(lambda locations: click.echo(f"Recorded {len(locations)} location(s)") if locations else None)
    try:
        poller.start()
    except KeyboardInterrupt:
        click.echo("\nStopping poller...")


@main.command()
@click.option("--host", "-h", help="Host to bind to")
@click.option("--port", "-p", type=int, help="Port to bind to")
def web(host, port):
    """Start the web interface."""
    config = get_config()
    database = LocationDatabase(config["db_path"])
    handler = ICloudAuth(config["username"], config["password"]) if config["username"] else None
    app = create_app(database, handler)
    host = host or config["web_host"]
    port = port or config["web_port"]
    click.echo(f"Starting web server at http://{host}:{port}")
    app.run(host=host, port=port, debug=False)


@main.command()
@click.option("--username", "-u", help="iCloud username (Apple ID)")
@click.option("--password", "-p", help="iCloud password")
@click.option("--host", help="Web server host")
@click.option("--port", type=int, help="Web server port")
def start(username, password, host, port):
    """Start both the poller and web interface."""
    config = get_config()
    username = username or config["username"]
    password = password or config["password"]
    host = host or config["web_host"]
    port = port or config["web_port"]
    if not username:
        click.echo("Error: ICLOUD_USERNAME is required", err=True)
        sys.exit(1)

    handler = ICloudAuth(username, password)
    database = LocationDatabase(config["db_path"])
    poller = LocationPoller(
        auth=handler,
        database=database,
        min_interval=config["min_interval"],
        max_interval=config["max_interval"],
    )
    app = create_app(database, handler)

    click.echo("Starting Find My Timeline")
    click.echo(f"  Polling interval: {config['min_interval']}-{config['max_interval']} minutes")
    click.echo(f"  Web interface: http://{host}:{port}")
    click.echo(f"  Database: {config['db_path']}")

    Thread(target=poller.start, daemon=True).start()
    try:
        app.run(host=host, port=port, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        click.echo("\nShutting down...")
        poller.stop()


@main.command()
def stats():
    """Show database statistics."""
    config = get_config()
    db_path = Path(config["db_path"])
    if not db_path.exists():
        click.echo("No database found. Run 'poll' first.")
        return
    database = LocationDatabase(db_path)
    devices = database.get_devices()
    click.echo(f"Database: {db_path}")
    click.echo(f"Total locations: {database.get_location_count():,}")
    click.echo(f"Devices: {len(devices)}")
    for device in devices:
        latest = database.get_latest_location(device["id"])
        click.echo(f"\n  {device['name']} ({device['device_display_name']})")
        click.echo(f"    Locations: {database.get_location_count(device['id']):,}")
        click.echo(f"    Last seen: {latest['timestamp'] if latest else 'Never'}")


@main.command()
def devices():
    """List all tracked devices."""
    config = get_config()
    db_path = Path(config["db_path"])
    if not db_path.exists():
        click.echo("No database found. Run 'poll' first.")
        return
    database = LocationDatabase(db_path)
    for device in database.get_devices():
        latest = database.get_latest_location(device["id"])
        click.echo(f"  {device['name']}")
        click.echo(f"    Type: {device['device_display_name']}")
        click.echo(f"    ID: {device['id']}")
        if latest:
            click.echo(f"    Last location: ({latest['latitude']:.6f}, {latest['longitude']:.6f})")
            click.echo(f"    Last seen: {latest['timestamp']}")
        click.echo()


if __name__ == "__main__":
    main()
