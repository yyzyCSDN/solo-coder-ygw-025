from __future__ import annotations

from typing import Any

from .engine import CleanroomStore
from .operations import EnvironmentalControl
from .rules import contamination_scope
from .workflows import SafetyWorkflows


class CleanroomCoordinator:
    """Application layer joining facility evidence, control and safety workflows."""

    def __init__(self, store: CleanroomStore) -> None:
        self.store = store
        self.control = EnvironmentalControl(store)
        self.workflows = SafetyWorkflows(store)

    def commission_pressure(self, cycle_id: str, pressures: dict[str, float]) -> dict[str, Any]:
        for room, value in pressures.items():
            self.store.record_evidence(room, "pressure", value, source="commissioning-kit")
        return self.control.pressure_plan(cycle_id, pressures)

    def start_occupancy(self, request_id: str, room_id: str, checks: dict[str, bool]) -> dict[str, Any]:
        record = self.workflows.open(request_id, "occupancy", room_id, "preparation", checks=checks)
        self.store.set_room_state(room_id, "reserved" if all(checks.values()) else "held")
        return record

    def start_transfer(self, request_id: str, room_id: str, material_id: str, door_contacts: tuple[bool, bool]) -> dict[str, Any]:
        if all(door_contacts):
            return self.workflows.open(request_id, "transfer", room_id, "blocked", material_id=material_id, reason="both-doors-open")
        return self.workflows.open(request_id, "transfer", room_id, "loaded", material_id=material_id, contacts=list(door_contacts))

    def maintenance_takeover(self, request_id: str, asset_id: str, actor: str, affected_room: str) -> dict[str, Any]:
        self.store.set_room_state(affected_room, "maintenance-hold")
        return self.store.command_once(request_id, asset_id, "maintenance-takeover", actor=actor, affected_room=affected_room)

    def assess_filter(self, unit_id: str) -> dict[str, Any]:
        return self.control.filter_health(unit_id)

    def allocate_air(self, cycle_id: str, requests: list[dict[str, Any]], capacity: float) -> dict[str, Any]:
        return self.control.allocate_shared_air(cycle_id, requests, capacity)

    def start_disinfection(self, request_id: str, room_id: str, minutes: int) -> dict[str, Any]:
        self.store.set_room_state(room_id, "disinfecting")
        return self.workflows.open(request_id, "disinfection", room_id, "dose", contact_minutes=int(minutes))

    def report_contamination(self, incident_id: str, origin_room: str, open_doors: set[tuple[str, str]], evidence_sequences: list[int]) -> dict[str, Any]:
        affected = contamination_scope(origin_room, self.store.pressure_edges(), open_doors)
        for room in affected:
            self.store.set_room_state(room, "isolated")
        return self.store.save_incident(incident_id, origin_room, affected, evidence_sequences)

    def emergency_ventilation(self, request_id: str, room_id: str, smoke: bool) -> dict[str, Any]:
        workflow = self.workflows.open(request_id, "emergency", room_id, "takeover", smoke=smoke)
        command = self.store.command_once(f"{request_id}:vent", room_id, "emergency-exhaust", smoke=smoke)
        return {"workflow": workflow, "command": command}

    def request_release(self, request_id: str, room_id: str, checks: dict[str, bool]) -> dict[str, Any]:
        record = self.workflows.open(request_id, "release", room_id, "collecting", checks=checks)
        decision = "qualified" if checks and all(checks.values()) else "held"
        return self.workflows.advance(record["workflow_id"], decision, checks=checks)

    def assess_sensor(self, asset_id: str, signal: str) -> dict[str, Any]:
        return self.control.assess_probe(asset_id, signal)

    def plan_heat_recovery(self, request_id: str, unit_id: str, efficiency: float, contamination_open: bool) -> dict[str, Any]:
        self.store.record_evidence(unit_id, "recovery_efficiency", efficiency, source="heat-controller")
        bypass = contamination_open or efficiency < 0.4
        command = self.store.command_once(request_id, unit_id, "bypass-heat-recovery" if bypass else "use-heat-recovery", efficiency=efficiency)
        return {"bypass": bypass, "command": command}
