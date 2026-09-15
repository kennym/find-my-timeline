"""SQLite database for storing location history."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator


class LocationDatabase:
    """Manages SQLite database for device location history."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS devices (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    device_display_name TEXT,
                    device_class TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    horizontal_accuracy REAL,
                    position_type TEXT,
                    battery_level REAL,
                    timestamp TIMESTAMP NOT NULL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES devices(id)
                );

                CREATE INDEX IF NOT EXISTS idx_locations_device_id
                    ON locations(device_id);
                CREATE INDEX IF NOT EXISTS idx_locations_timestamp
                    ON locations(timestamp);
                CREATE INDEX IF NOT EXISTS idx_locations_device_timestamp
                    ON locations(device_id, timestamp);
            """)

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def upsert_device(
        self,
        device_id: str,
        name: str,
        device_display_name: str | None = None,
        device_class: str | None = None,
    ) -> None:
        """Insert or update a device."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO devices (id, name, device_display_name, device_class, last_seen)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    device_display_name = excluded.device_display_name,
                    device_class = excluded.device_class,
                    last_seen = CURRENT_TIMESTAMP
                """,
                (device_id, name, device_display_name, device_class),
            )

    def record_location(
        self,
        device_id: str,
        latitude: float,
        longitude: float,
        timestamp: datetime,
        horizontal_accuracy: float | None = None,
        position_type: str | None = None,
        battery_level: float | None = None,
    ) -> int:
        """Record a location point for a device. Returns the location ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO locations
                    (device_id, latitude, longitude, horizontal_accuracy,
                     position_type, battery_level, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    device_id,
                    latitude,
                    longitude,
                    horizontal_accuracy,
                    position_type,
                    battery_level,
                    timestamp,
                ),
            )
            return cursor.lastrowid

    def get_devices(self) -> list[dict]:
        """Get all known devices."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT d.*, EXISTS(SELECT 1 FROM locations l WHERE l.device_id = d.id) AS has_location FROM devices d ORDER BY d.last_seen DESC"
            ).fetchall()
            devices = []
            for row in rows:
                device = dict(row)
                device['has_location'] = bool(device['has_location'])
                devices.append(device)
            return devices

    def get_locations(
        self,
        device_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Get location history with optional filters."""
        query = "SELECT * FROM locations WHERE 1=1"
        params: list = []

        if device_id:
            query += " AND device_id = ?"
            params.append(device_id)

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_latest_location(self, device_id: str) -> dict | None:
        """Get the most recent location for a device."""
        locations = self.get_locations(device_id=device_id, limit=1)
        return locations[0] if locations else None

    def get_location_count(self, device_id: str | None = None) -> int:
        """Get total number of recorded locations."""
        query = "SELECT COUNT(*) FROM locations"
        params: list = []

        if device_id:
            query += " WHERE device_id = ?"
            params.append(device_id)

        with self._get_connection() as conn:
            return conn.execute(query, params).fetchone()[0]
