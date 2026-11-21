"""Monitor CLI para visualizar el estado de espacios publicados por MQTT."""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional

import paho.mqtt.client as mqtt

DEFAULT_BROKER = os.getenv("MQTT_BROKER", "localhost")
DEFAULT_PORT = int(os.getenv("MQTT_PORT", "1883"))
DEFAULT_PARKING_ID = os.getenv("PARKING_ID", "estacionamiento-central")
EXPECTED_KEYS = {"spot_id", "timestamp", "occupied", "distance_cm"}


@dataclass
class SpotStatus:
    parking_id: str
    spot_id: str
    timestamp: str
    occupied: bool
    distance_cm: float
    event: str = "updated"


class ParkingMonitor:
    def __init__(self, parking_id: str) -> None:
        self.parking_id = parking_id
        self.latest: Dict[str, SpotStatus] = {}
        self._lock = threading.Lock()

    def handle_message(self, message: mqtt.MQTTMessage) -> bool:
        try:
            data = json.loads(message.payload.decode("utf-8"))
            if not EXPECTED_KEYS.issubset(data):
                return False
            status = SpotStatus(
                parking_id=data.get("parking_id", self.parking_id),
                spot_id=str(data["spot_id"]),
                timestamp=str(data["timestamp"]),
                occupied=bool(data["occupied"]),
                distance_cm=float(data["distance_cm"]),
                event=str(data.get("event", "updated")),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return False

        with self._lock:
            self.latest[status.spot_id] = status
        return True

    def render(self) -> str:
        with self._lock:
            rows = sorted(self.latest.values(), key=lambda item: item.spot_id)
        occupied = sum(1 for status in rows if status.occupied)
        free = len(rows) - occupied

        lines = [
            "PANEL DE OCUPACION - HC-SR04",
            f"Estacionamiento: {self.parking_id}",
            f"Ocupados: {occupied} | Libres: {free} | Total: {len(rows)}",
            f"{'Espacio':<10} {'Estado':<12} {'Distancia':>12} {'Evento':<12}",
            "-" * 52,
        ]
        for status in rows:
            state = "OCUPADO" if status.occupied else "LIBRE"
            lines.append(
                f"{status.spot_id:<10} {state:<12} {status.distance_cm:>9.2f} cm "
                f"{status.event:<12}"
            )
        return "\n".join(lines)


def build_topic(parking_id: str) -> str:
    if parking_id == "#":
        return "iot/#"
    return f"iot/{parking_id}/#"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker", default=DEFAULT_BROKER)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--parking-id",
        default=DEFAULT_PARKING_ID,
        help="Id de estacionamiento. Usa # para escuchar todos.",
    )
    parser.add_argument(
        "--once",
        nargs="?",
        const="1",
        type=str,
        help="Espera lecturas y termina; valor opcional: cantidad de espacios",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Segundos de espera cuando se usa --once",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    monitor = ParkingMonitor(args.parking_id)
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"monitor-{args.parking_id}",
    )

    def on_message(_client, _userdata, message: mqtt.MQTTMessage) -> None:
        monitor.handle_message(message)

    client.on_message = on_message

    try:
        client.connect(args.broker, args.port, keepalive=60)
        client.loop_start()
        topic = build_topic(args.parking_id)
        client.subscribe(topic, qos=0)

        if not args.once:
            while True:
                time.sleep(2.0)
                print("\n" + monitor.render(), flush=True)

        deadline = time.monotonic() + max(0.1, args.timeout)
        expected = max(1, int(args.once))
        while time.monotonic() < deadline and len(monitor.latest) < expected:
            time.sleep(0.05)

        print(monitor.render())
    except KeyboardInterrupt:
        print("\nMonitor detenido por el usuario")
    except Exception as exc:
        print(f"No se pudo conectar al broker MQTT: {exc}", file=sys.stderr)
        return 2
    finally:
        client.loop_stop()
        client.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
