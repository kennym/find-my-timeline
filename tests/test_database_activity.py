import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from find_my_timeline.database import LocationDatabase


class DeviceActivityTests(unittest.TestCase):
    def test_devices_expose_activity_from_location_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = LocationDatabase(Path(tmp) / "locations.db")
            db.upsert_device("active", "Active device")
            db.upsert_device("inactive", "Inactive device")
            db.record_location(
                "active", 1.0, 2.0, datetime(2026, 9, 15, 12, 0, 0)
            )

            devices = {device["id"]: device for device in db.get_devices()}

            self.assertTrue(devices["active"]["has_location"])
            self.assertFalse(devices["inactive"]["has_location"])


if __name__ == "__main__":
    unittest.main()
