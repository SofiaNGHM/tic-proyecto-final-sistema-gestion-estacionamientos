"""Pruebas del parser y panel del monitor MQTT."""

from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

from monitor.monitor import ParkingMonitor


def make_message(data: dict) -> SimpleNamespace:
    return SimpleNamespace(payload=json.dumps(data).encode("utf-8"))


class ParkingMonitorTests(unittest.TestCase):
    def test_accepts_valid_measurement(self):
        monitor = ParkingMonitor("estacionamiento-central")
        accepted = monitor.handle_message(
            make_message(
                {
                    "parking_id": "estacionamiento-central",
                    "spot_id": "A-01",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "occupied": True,
                    "distance_cm": 15.0,
                    "event": "occupied",
                }
            )
        )
        self.assertTrue(accepted)
        self.assertIn("A-01", monitor.latest)

    def test_rejects_invalid_measurement(self):
        monitor = ParkingMonitor("estacionamiento-central")
        accepted = monitor.handle_message(
            make_message({"occupied": "not-valid", "distance_cm": None})
        )
        self.assertFalse(accepted)
        self.assertEqual(monitor.latest, {})

    def test_renders_totals(self):
        monitor = ParkingMonitor("estacionamiento-central")
        monitor.handle_message(
            make_message(
                {
                    "parking_id": "estacionamiento-central",
                    "spot_id": "A-01",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "occupied": True,
                    "distance_cm": 15.0,
                    "event": "occupied",
                }
            )
        )
        monitor.handle_message(
            make_message(
                {
                    "parking_id": "estacionamiento-central",
                    "spot_id": "A-02",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "occupied": False,
                    "distance_cm": 70.0,
                    "event": "freed",
                }
            )
        )
        output = monitor.render()
        self.assertIn("Ocupados: 1", output)
        self.assertIn("Libres: 1", output)
        self.assertIn("OCUPADO", output)
        self.assertIn("LIBRE", output)


if __name__ == "__main__":
    unittest.main()
