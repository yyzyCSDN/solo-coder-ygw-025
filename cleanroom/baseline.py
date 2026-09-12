from __future__ import annotations

from typing import Any

from .engine import CleanroomStore


DEFAULT_FACILITY = {
    "rooms": [
        {"room_id": "or-a", "grade": "B", "supply_capacity": 42.0, "exhaust_capacity": 35.0},
        {"room_id": "buffer-a", "grade": "C", "supply_capacity": 25.0, "exhaust_capacity": 27.0},
        {"room_id": "corridor", "grade": "D", "supply_capacity": 18.0, "exhaust_capacity": 22.0},
    ],
    "pressure_edges": [
        {"cleaner_room": "or-a", "dirtier_room": "buffer-a", "minimum_delta": 8.0},
        {"cleaner_room": "buffer-a", "dirtier_room": "corridor", "minimum_delta": 5.0},
    ],
}


def install_facility(store: CleanroomStore, facility: dict[str, Any] | None = None) -> None:
    definition = facility or DEFAULT_FACILITY
    for room in definition["rooms"]:
        store.configure_room(**room)
    for edge in definition["pressure_edges"]:
        store.connect_pressure(**edge)
