"""Pruebas para el simulador HC-SR04 y el monitor MQTT."""

from __future__ import annotations

import json
import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from parking_simulator import (
    OCCUPIED_THRESHOLD_CM,
    ParkingSpotSimulator,
    SpotMeasurement,
    build_topic,
    create_spots,
    publish_measurements,
)

class FixedRandom:
    """RNG simple para probar transiciones sin valores aleatorios."""

    def random(self) -> float:
        return 0.99

    def gauss(self, _mu: float, _sigma: float) -> float:
        return 0.0

    def uniform(self, low: float, high: float) -> float:
        return (low + high) / 2.0


class ParkingSimulatorTests(unittest.TestCase):
    def test_topic_format(self):
        self.assertEqual(
            build_topic("estacionamiento-central", "A-01"),
            "iot/estacionamiento-central/espacio/A-01/estado",
        )

    def test_create_spots_generates_unique_ids(self):
        spots = create_spots(8, "estacionamiento-central")
        self.assertEqual([spot.spot_id for spot in spots], [f"A-{i:02d}" for i in range(1, 9)])

    def test_measurement_is_consistent_with_threshold(self):
        simulator = ParkingSpotSimulator(
            "A-01",
            "estacionamiento-central",
            rng=random.Random(42),
        )
        previous = None
        for _ in range(50):
            measurement = simulator.sample(previous)
            previous = measurement
            self.assertEqual(measurement.occupied, measurement.distance_cm <= OCCUPIED_THRESHOLD_CM)
            self.assertEqual(measurement.sensor_model, "HC-SR04")

    def test_json_payload_contains_required_fields(self):
        measurement = SpotMeasurement(
            parking_id="estacionamiento-central",
            spot_id="A-02",
            timestamp="2026-01-01T00:00:00+00:00",
            occupied=True,
            distance_cm=15.5,
            threshold_cm=30.0,
            sensor_model="HC-SR04",
            event="occupied",
        )
        payload = json.loads(measurement.to_json())
        expected = {
            "parking_id",
            "spot_id",
            "timestamp",
            "occupied",
            "distance_cm",
            "threshold_cm",
            "sensor_model",
            "event",
        }
        self.assertEqual(set(payload), expected)

    def test_state_change_events(self):
        simulator_occupied = ParkingSpotSimulator(
            "A-01", "estacionamiento-central", rng=FixedRandom(), initial_occupied=True
        )
        free = SpotMeasurement(
            "estacionamiento-central", "A-01", "", False, 60.0, 30.0, "HC-SR04", "unchanged"
        )
        self.assertEqual(simulator_occupied.sample(free).event, "occupied")

        simulator_free = ParkingSpotSimulator(
            "A-02", "estacionamiento-central", rng=FixedRandom(), initial_occupied=False
        )
        occupied = SpotMeasurement(
            "estacionamiento-central", "A-02", "", True, 20.0, 30.0, "HC-SR04", "unchanged"
        )
        simulator_free._p_becomes_free = 1.0
        self.assertEqual(simulator_free.sample(occupied).event, "freed")

    def test_publishes_all_spaces(self):
        class FakeClient:
            def __init__(self) -> None:
                self.payloads = []

            def publish(self, topic: str, payload: str, qos: int, retain: bool):
                del qos, retain
                self.payloads.append((topic, payload))
                return SimpleNamespace(rc=0)

        spots = create_spots(3, "estacionamiento-central", rng=FixedRandom())
        client = FakeClient()
        published = publish_measurements(client, "estacionamiento-central", spots, {})
        self.assertEqual(published, 3)
        self.assertEqual(len(client.payloads), 3)
        for topic, payload in client.payloads:
            self.assertTrue(topic.startswith("iot/estacionamiento-central/espacio/"))
            self.assertEqual(set(json.loads(payload)), {"parking_id", "spot_id", "timestamp", "occupied", "distance_cm", "threshold_cm", "sensor_model", "event"})
            self.assertGreater(json.loads(payload)["distance_cm"], 0)


if __name__ == "__main__":
    unittest.main()
