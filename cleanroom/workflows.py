from __future__ import annotations

from typing import Any

from .engine import CleanroomStore, InvalidStage


TRANSITIONS = {
    "occupancy": {"preparation": {"in-use", "blocked"}, "in-use": {"turnover"}, "turnover": {"released", "blocked"}},
    "transfer": {"loaded": {"disinfecting", "blocked"}, "disinfecting": {"handoff", "blocked"}, "handoff": {"complete"}, "blocked": set()},
    "disinfection": {"dose": {"contact", "invalid"}, "contact": {"purge", "invalid"}, "purge": {"verified", "blocked"}},
    "emergency": {"takeover": {"stabilizing"}, "stabilizing": {"reconcile", "blocked"}, "reconcile": {"complete", "isolated"}},
    "release": {"collecting": {"held", "qualified"}, "qualified": {"released"}},
}


class SafetyWorkflows:
    def __init__(self, store: CleanroomStore) -> None:
        self.store = store

    def open(self, workflow_id: str, kind: str, room_id: str, stage: str, **payload: Any) -> dict[str, Any]:
        if kind not in TRANSITIONS or stage not in TRANSITIONS[kind]:
            raise InvalidStage(f"{kind}:{stage}")
        return self.store.put_workflow(workflow_id, kind, room_id, stage, payload)

    def advance(self, workflow_id: str, next_stage: str, **evidence: Any) -> dict[str, Any]:
        current = self.store.workflow(workflow_id)
        allowed = TRANSITIONS[current["kind"]].get(current["stage"], set())
        if next_stage not in allowed:
            raise InvalidStage(f"{current['kind']}:{current['stage']}->{next_stage}")
        payload = {**current["payload"], "last_evidence": evidence}
        return self.store.put_workflow(workflow_id, current["kind"], current["room_id"], next_stage, payload)

    def resume(self, workflow_id: str, observed_stage: str) -> dict[str, Any]:
        current = self.store.workflow(workflow_id)
        if current["stage"] != observed_stage:
            raise InvalidStage(f"persisted={current['stage']}, observed={observed_stage}")
        return current
