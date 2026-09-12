from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CleanroomError(Exception):
    pass


class UnknownRoom(CleanroomError):
    pass


class InvalidStage(CleanroomError):
    pass


class CleanroomStore:
    """SQLite ledger for rooms, evidence, commands and staged safety work."""

    def __init__(self, database: str = ":memory:") -> None:
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        with self.connection:
            self.connection.executescript(
                """
                PRAGMA foreign_keys=ON;
                CREATE TABLE IF NOT EXISTS rooms(
                    room_id TEXT PRIMARY KEY, grade TEXT NOT NULL, state TEXT NOT NULL,
                    supply_capacity REAL NOT NULL, exhaust_capacity REAL NOT NULL,
                    config_version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS pressure_edges(
                    cleaner_room TEXT NOT NULL, dirtier_room TEXT NOT NULL,
                    minimum_delta REAL NOT NULL,
                    PRIMARY KEY(cleaner_room, dirtier_room));
                CREATE TABLE IF NOT EXISTS evidence(
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_id TEXT NOT NULL, signal TEXT NOT NULL, value REAL NOT NULL,
                    quality TEXT NOT NULL, source TEXT NOT NULL,
                    calibration_version TEXT NOT NULL, observed_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS commands(
                    command_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command_key TEXT UNIQUE NOT NULL, asset_id TEXT NOT NULL,
                    kind TEXT NOT NULL, parameters TEXT NOT NULL,
                    status TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS workflows(
                    workflow_id TEXT PRIMARY KEY, kind TEXT NOT NULL,
                    room_id TEXT NOT NULL, stage TEXT NOT NULL,
                    revision INTEGER NOT NULL, payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(room_id) REFERENCES rooms(room_id));
                CREATE TABLE IF NOT EXISTS incidents(
                    incident_id TEXT PRIMARY KEY, origin_room TEXT NOT NULL,
                    open INTEGER NOT NULL, affected_rooms TEXT NOT NULL,
                    evidence_sequences TEXT NOT NULL, updated_at TEXT NOT NULL);
                """
            )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.lock, self.connection:
            yield self.connection

    def configure_room(self, room_id: str, grade: str, *, supply_capacity: float, exhaust_capacity: float, config_version: int = 1) -> dict[str, Any]:
        with self.transaction() as conn:
            conn.execute(
                """INSERT INTO rooms VALUES(?,?,?,?,?,?)
                ON CONFLICT(room_id) DO UPDATE SET grade=excluded.grade,
                supply_capacity=excluded.supply_capacity,
                exhaust_capacity=excluded.exhaust_capacity,
                config_version=excluded.config_version""",
                (room_id, grade, "available", supply_capacity, exhaust_capacity, config_version),
            )
        return self.room(room_id)

    def room(self, room_id: str) -> dict[str, Any]:
        row = self.connection.execute("SELECT * FROM rooms WHERE room_id=?", (room_id,)).fetchone()
        if row is None:
            raise UnknownRoom(room_id)
        return dict(row)

    def rooms(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self.connection.execute("SELECT * FROM rooms ORDER BY room_id")]

    def set_room_state(self, room_id: str, state: str) -> dict[str, Any]:
        self.room(room_id)
        with self.transaction() as conn:
            conn.execute("UPDATE rooms SET state=? WHERE room_id=?", (state, room_id))
        return self.room(room_id)

    def connect_pressure(self, cleaner_room: str, dirtier_room: str, minimum_delta: float) -> None:
        self.room(cleaner_room)
        self.room(dirtier_room)
        with self.transaction() as conn:
            conn.execute("INSERT OR REPLACE INTO pressure_edges VALUES(?,?,?)", (cleaner_room, dirtier_room, float(minimum_delta)))

    def pressure_edges(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self.connection.execute("SELECT * FROM pressure_edges")]

    def record_evidence(self, asset_id: str, signal: str, value: float, *, source: str, quality: str = "good", calibration_version: str = "v1", observed_at: str | None = None) -> dict[str, Any]:
        stamp = observed_at or utc_now()
        with self.transaction() as conn:
            cursor = conn.execute(
                """INSERT INTO evidence(asset_id,signal,value,quality,source,
                calibration_version,observed_at) VALUES(?,?,?,?,?,?,?)""",
                (asset_id, signal, float(value), quality, source, calibration_version, stamp),
            )
        return dict(self.connection.execute("SELECT * FROM evidence WHERE sequence=?", (cursor.lastrowid,)).fetchone())

    def evidence(self, asset_id: str, signal: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM evidence WHERE asset_id=? AND signal=? ORDER BY sequence", (asset_id, signal)
        ).fetchall()
        return [dict(row) for row in rows]

    def command_once(self, command_key: str, asset_id: str, kind: str, **parameters: Any) -> dict[str, Any]:
        existing = self.connection.execute("SELECT * FROM commands WHERE command_key=?", (command_key,)).fetchone()
        if existing is not None:
            result = dict(existing)
            result["parameters"] = json.loads(result["parameters"])
            result["duplicate"] = True
            return result
        with self.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO commands(command_key,asset_id,kind,parameters,status,created_at) VALUES(?,?,?,?,?,?)",
                (command_key, asset_id, kind, json.dumps(parameters, sort_keys=True), "requested", utc_now()),
            )
        result = dict(self.connection.execute("SELECT * FROM commands WHERE command_id=?", (cursor.lastrowid,)).fetchone())
        result["parameters"] = json.loads(result["parameters"])
        result["duplicate"] = False
        return result

    def put_workflow(self, workflow_id: str, kind: str, room_id: str, stage: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.room(room_id)
        current = self.connection.execute("SELECT revision FROM workflows WHERE workflow_id=?", (workflow_id,)).fetchone()
        revision = int(current["revision"]) + 1 if current else 1
        with self.transaction() as conn:
            conn.execute(
                """INSERT INTO workflows VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(workflow_id) DO UPDATE SET stage=excluded.stage,
                revision=excluded.revision,payload=excluded.payload,updated_at=excluded.updated_at""",
                (workflow_id, kind, room_id, stage, revision, json.dumps(payload, sort_keys=True), utc_now()),
            )
        return self.workflow(workflow_id)

    def workflow(self, workflow_id: str) -> dict[str, Any]:
        row = self.connection.execute("SELECT * FROM workflows WHERE workflow_id=?", (workflow_id,)).fetchone()
        if row is None:
            raise InvalidStage(f"unknown workflow: {workflow_id}")
        result = dict(row)
        result["payload"] = json.loads(result["payload"])
        return result

    def save_incident(self, incident_id: str, origin_room: str, affected: list[str], sequences: list[int]) -> dict[str, Any]:
        with self.transaction() as conn:
            conn.execute(
                """INSERT INTO incidents VALUES(?,?,?,?,?,?)
                ON CONFLICT(incident_id) DO UPDATE SET affected_rooms=excluded.affected_rooms,
                evidence_sequences=excluded.evidence_sequences,updated_at=excluded.updated_at""",
                (incident_id, origin_room, 1, json.dumps(sorted(set(affected))), json.dumps(sequences), utc_now()),
            )
        row = self.connection.execute("SELECT * FROM incidents WHERE incident_id=?", (incident_id,)).fetchone()
        result = dict(row)
        result["affected_rooms"] = json.loads(result["affected_rooms"])
        result["evidence_sequences"] = json.loads(result["evidence_sequences"])
        return result

    def snapshot(self) -> dict[str, Any]:
        tables = ("rooms", "pressure_edges", "evidence", "commands", "workflows", "incidents")
        return {name: [dict(row) for row in self.connection.execute(f"SELECT * FROM {name}")] for name in tables}

    def close(self) -> None:
        self.connection.close()
