from __future__ import annotations

from typing import Any

from .engine import CleanroomStore
from .rules import pressure_violations, proportional_air_allocation, stable_value


class EnvironmentalControl:
    def __init__(self, store: CleanroomStore) -> None:
        self.store = store

    def pressure_plan(self, cycle_id: str, pressures: dict[str, float]) -> dict[str, Any]:
        violations = pressure_violations(self.store.pressure_edges(), pressures)
        commands = []
        for item in violations:
            room = item["cleaner_room"]
            if item["reason"] == "missing-evidence":
                continue
            commands.append(self.store.command_once(
                f"{cycle_id}:pressure:{room}", room, "increase-supply",
                deficit=round(item["minimum_delta"] - item["actual_delta"], 3),
            ))
        return {"cycle_id": cycle_id, "safe": not violations, "violations": violations, "commands": commands}

    def allocate_shared_air(self, cycle_id: str, requests: list[dict[str, Any]], capacity: float) -> dict[str, Any]:
        grants = proportional_air_allocation(requests, capacity)
        commands = [
            self.store.command_once(f"{cycle_id}:air:{row['room']}", row["room"], "set-airflow", granted=row["granted"])
            for row in grants
        ]
        return {"cycle_id": cycle_id, "capacity": capacity, "grants": grants, "commands": commands}

    def assess_probe(self, asset_id: str, signal: str) -> dict[str, Any]:
        samples = self.store.evidence(asset_id, signal)
        assessment = stable_value(samples)
        return {"asset_id": asset_id, "signal": signal, "sample_sequences": [s["sequence"] for s in samples], **assessment}

    def filter_health(self, unit_id: str, resistance_signal: str = "filter_resistance") -> dict[str, Any]:
        samples = self.store.evidence(unit_id, resistance_signal)
        normalized = [sample["value"] for sample in samples if sample["quality"] == "good"]
        if len(normalized) < 2:
            return {"unit_id": unit_id, "status": "unknown", "trend": None}
        trend = normalized[-1] - normalized[0]
        return {"unit_id": unit_id, "status": "degrading" if trend >= 2 else "stable", "trend": round(trend, 3)}
