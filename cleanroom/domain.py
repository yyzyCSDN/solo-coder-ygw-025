from __future__ import annotations
from typing import Any

class CleanroomCoordinator:
    """Current cleanroom paths persist room, ventilation and release evidence."""
    def __init__(self, service: Any) -> None: self.service=service

    def pressure_action(self, room: str, pressure: float, target: float) -> dict:
        if pressure < target: return {"room":room,"action":"set_supply","delta":target-pressure,"basis":"single-room"}
        if pressure > target: return {"room":room,"action":"set_exhaust","delta":pressure-target,"basis":"single-room"}
        return {"room":room,"action":"hold","delta":0.0,"basis":"single-room"}
    def occupancy_job(self, request_id: str, room: str, checks: dict) -> dict:
        return self.service.baseline.create_job("room_occupancy",request_id,[room],checks=dict(checks),phase="preparation")
    def pass_box_policy(self, left_open: bool, right_open: bool) -> bool:
        return not (left_open and right_open)
    def maintenance_hold(self, asset_id: str, actor: str) -> dict:
        return self.service.baseline.issue_action(asset_id,"maintenance_hold",f"maintenance:{asset_id}:{actor}",actor=actor)
    def filter_condition(self, resistance: float, limit: float) -> str:
        return "alarm" if resistance >= limit else "normal"
    def allocate_air(self, requests: list[dict], capacity: float) -> list[dict]:
        remaining=float(capacity); result=[]
        for row in requests:
            granted=min(remaining,float(row["requested"])); remaining-=granted
            result.append({"room":row["room"],"granted":granted,"basis":"request-order"})
        return result
    def disinfection_job(self, request_id: str, room: str, minutes: int) -> dict:
        return self.service.baseline.create_job("disinfection",request_id,[room],phase="dose",minutes=int(minutes),restart_policy="full-cycle")
    def contamination_incident(self, request_id: str, room: str, particle_count: float) -> dict:
        return self.service.baseline.create_job("contamination_incident",request_id,[room],group_key=room,particle_count=float(particle_count),scope=[room])
    def emergency_ventilation(self, request_id: str, room: str, smoke: bool) -> dict:
        action=self.service.baseline.issue_action(room,"emergency_vent",request_id,actor="safety",smoke=bool(smoke))
        return self.service.baseline.create_job("emergency_ventilation",request_id+":job",[room],action_id=action["action_id"],phase="takeover")
    def release_job(self, request_id: str, room: str, checks: dict) -> dict:
        return self.service.baseline.create_job("room_release",request_id,[room],checks=dict(checks),decision="ready" if all(checks.values()) else "hold",basis="single-snapshot")
    def sensor_assessment(self, request_id: str, probe: str, samples: list[dict]) -> dict:
        usable=[row for row in samples if row.get("quality","good")!="bad"]
        value=usable[-1]["value"] if usable else None
        return self.service.baseline.create_job("sensor_assessment",request_id,[probe],value=value,usable=len(usable),basis="latest-usable")
    def heat_recovery_job(self, request_id: str, unit: str, efficiency: float) -> dict:
        self.service.baseline.record_signal(unit,"recovery_efficiency",efficiency,source="controller")
        return self.service.baseline.create_job("heat_recovery",request_id,[unit],efficiency=float(efficiency),bypass=False,basis="current-efficiency")
