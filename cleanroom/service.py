from __future__ import annotations

from typing import Any

from .baseline import install_facility
from .domain import CleanroomCoordinator
from .engine import CleanroomStore


class CleanroomService:
    def __init__(self, database: str = ":memory:", *, seed: bool = True) -> None:
        self.store = CleanroomStore(database)
        if seed and not self.store.rooms():
            install_facility(self.store)
        self.coordinator = CleanroomCoordinator(self.store)

    def record_reading(self, asset_id: str, signal: str, value: float, **metadata: Any) -> dict[str, Any]:
        return self.store.record_evidence(asset_id, signal, value, source=metadata.pop("source", "operator"), **metadata)

    def commission_pressure(self, cycle_id: str, pressures: dict[str, float]) -> dict[str, Any]:
        return self.coordinator.commission_pressure(cycle_id, pressures)

    def start_occupancy(self, request_id: str, room_id: str, checks: dict[str, bool]) -> dict[str, Any]:
        return self.coordinator.start_occupancy(request_id, room_id, checks)

    def start_transfer(self, request_id: str, room_id: str, material_id: str, contacts: tuple[bool, bool]) -> dict[str, Any]:
        return self.coordinator.start_transfer(request_id, room_id, material_id, contacts)

    def maintenance_takeover(self, request_id: str, asset_id: str, actor: str, room_id: str) -> dict[str, Any]:
        return self.coordinator.maintenance_takeover(request_id, asset_id, actor, room_id)

    def assess_filter(self, unit_id: str) -> dict[str, Any]:
        return self.coordinator.assess_filter(unit_id)

    def allocate_air(self, cycle_id: str, requests: list[dict[str, Any]], capacity: float) -> dict[str, Any]:
        return self.coordinator.allocate_air(cycle_id, requests, capacity)

    def start_disinfection(self, request_id: str, room_id: str, minutes: int) -> dict[str, Any]:
        return self.coordinator.start_disinfection(request_id, room_id, minutes)

    def report_contamination(self, incident_id: str, origin_room: str, open_doors: set[tuple[str, str]], sequences: list[int]) -> dict[str, Any]:
        return self.coordinator.report_contamination(incident_id, origin_room, open_doors, sequences)

    def emergency_ventilation(self, request_id: str, room_id: str, smoke: bool) -> dict[str, Any]:
        return self.coordinator.emergency_ventilation(request_id, room_id, smoke)

    def request_release(self, request_id: str, room_id: str, checks: dict[str, bool]) -> dict[str, Any]:
        return self.coordinator.request_release(request_id, room_id, checks)

    def assess_sensor(self, asset_id: str, signal: str) -> dict[str, Any]:
        return self.coordinator.assess_sensor(asset_id, signal)

    def plan_heat_recovery(self, request_id: str, unit_id: str, efficiency: float, contaminated: bool) -> dict[str, Any]:
        return self.coordinator.plan_heat_recovery(request_id, unit_id, efficiency, contaminated)

    def health(self) -> dict[str, Any]:
        snapshot = self.store.snapshot()
        return {"status": "ok", "rooms": len(snapshot["rooms"]), "workflows": len(snapshot["workflows"]), "commands": len(snapshot["commands"])}

    def close(self) -> None:
        self.store.close()
