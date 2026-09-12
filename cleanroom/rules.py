from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


GRADE_RISK = {"A": 5, "B": 4, "C": 3, "D": 2, "unclassified": 1}


def pressure_violations(edges: list[dict[str, Any]], pressures: dict[str, float]) -> list[dict[str, Any]]:
    violations = []
    for edge in edges:
        clean = edge["cleaner_room"]
        dirty = edge["dirtier_room"]
        if clean not in pressures or dirty not in pressures:
            violations.append({**edge, "reason": "missing-evidence", "actual_delta": None})
            continue
        actual = pressures[clean] - pressures[dirty]
        if actual < edge["minimum_delta"]:
            violations.append({**edge, "reason": "reversed-or-small", "actual_delta": actual})
    return violations


def contamination_scope(origin: str, edges: list[dict[str, Any]], open_doors: set[tuple[str, str]]) -> list[str]:
    graph: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        pair = (edge["cleaner_room"], edge["dirtier_room"])
        reverse = (pair[1], pair[0])
        if pair in open_doors or reverse in open_doors:
            graph[pair[0]].add(pair[1])
            graph[pair[1]].add(pair[0])
    seen = {origin}
    queue = deque([origin])
    while queue:
        room = queue.popleft()
        for neighbor in graph[room] - seen:
            seen.add(neighbor)
            queue.append(neighbor)
    return sorted(seen)


def proportional_air_allocation(requests: list[dict[str, Any]], capacity: float) -> list[dict[str, Any]]:
    weighted = [(row, max(0.0, float(row["requested"])) * GRADE_RISK.get(row.get("grade", "unclassified"), 1)) for row in requests]
    total = sum(weight for _, weight in weighted)
    if total <= 0:
        return [{**row, "granted": 0.0} for row, _ in weighted]
    grants = []
    remaining = max(0.0, float(capacity))
    for index, (row, weight) in enumerate(weighted):
        fair = remaining if index == len(weighted) - 1 else min(float(row["requested"]), capacity * weight / total)
        fair = max(0.0, min(remaining, fair))
        grants.append({**row, "granted": round(fair, 3)})
        remaining -= fair
    return grants


def stable_value(samples: list[dict[str, Any]]) -> dict[str, Any]:
    usable = [sample for sample in samples if sample["quality"] == "good"]
    if not usable:
        return {"status": "unknown", "value": None, "sources": []}
    versions = {sample["calibration_version"] for sample in usable}
    values = [float(sample["value"]) for sample in usable[-3:]]
    if len(versions) > 1 or (len(values) > 1 and max(values) - min(values) > 2.0):
        return {"status": "conflict", "value": None, "sources": [s["source"] for s in usable]}
    return {"status": "trusted", "value": round(sum(values) / len(values), 3), "sources": [s["source"] for s in usable]}
