"""SQLite persistence. One file, zero infra. JSON columns for structured fields."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import (
    AuditEvent,
    Intervention,
    RecoveryCase,
)
from .audit_chain import chain_append, get_audit_chain

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
  case_id TEXT PRIMARY KEY,
  payment_id TEXT,
  customer_id TEXT,
  amount INTEGER,
  failure_class TEXT,
  status TEXT,
  group_tag TEXT,
  recovered_amount INTEGER DEFAULT 0,
  data TEXT NOT NULL,
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS actions (
  action_id TEXT PRIMARY KEY,
  case_id TEXT,
  action_type TEXT,
  status TEXT,
  scheduled_at TEXT,
  executed_at TEXT,
  cost_paise INTEGER DEFAULT 0,
  data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
  event_id TEXT PRIMARY KEY,
  ts TEXT,
  actor TEXT,
  event_type TEXT,
  case_id TEXT,
  payload TEXT,
  chain_hash TEXT,
  prev_hash TEXT,
  chain_index INTEGER
);
CREATE TABLE IF NOT EXISTS webhook_events (
  event_id TEXT PRIMARY KEY,
  processed_at TEXT NOT NULL,
  event_type TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_case ON audit(case_id);
CREATE INDEX IF NOT EXISTS idx_actions_case ON actions(case_id);
"""


def _dump(model) -> str:
    return model.model_dump_json()


class Store:
    def __init__(self, path: str | Path = "recovery.db") -> None:
        self.conn = sqlite3.connect(str(path), timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")       # concurrent webhook readers/writes
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    # ---- cases -------------------------------------------------------
    def upsert_case(self, case: RecoveryCase) -> None:
        self.conn.execute(
            "INSERT INTO cases (case_id,payment_id,customer_id,amount,failure_class,status,"
            "group_tag,recovered_amount,data,created_at) VALUES (?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(case_id) DO UPDATE SET status=excluded.status,"
            "recovered_amount=excluded.recovered_amount,data=excluded.data",
            (
                case.case_id, case.payment_id, case.customer.customer_id, case.amount,
                case.failure_class.value, case.status.value, case.group.value,
                case.recovered_amount, _dump(case), case.created_at,
            ),
        )
        self.conn.commit()

    def get_case(self, case_id: str) -> RecoveryCase | None:
        row = self.conn.execute(
            "SELECT data FROM cases WHERE case_id=?", (case_id,)
        ).fetchone()
        return RecoveryCase.model_validate_json(row["data"]) if row else None

    def get_case_by_payment(self, payment_id: str) -> RecoveryCase | None:
        row = self.conn.execute(
            "SELECT data FROM cases WHERE payment_id=? ORDER BY created_at DESC LIMIT 1",
            (payment_id,),
        ).fetchone()
        return RecoveryCase.model_validate_json(row["data"]) if row else None

    def get_case_by_reference(self, reference_id: str) -> RecoveryCase | None:
        # payment links are created with reference_id == case_id
        return self.get_case(reference_id)

    def get_case_by_customer_phone(self, phone: str) -> RecoveryCase | None:
        row = self.conn.execute(
            "SELECT data FROM cases "
            "WHERE json_extract(data,'$.customer.phone')=? "
            "AND status IN ('open','scheduled') ORDER BY created_at DESC LIMIT 1",
            (phone,),
        ).fetchone()
        return RecoveryCase.model_validate_json(row["data"]) if row else None

    def open_cases_with_active_promise(self) -> list[RecoveryCase]:
        rows = self.conn.execute(
            "SELECT data FROM cases WHERE status IN ('open','scheduled') "
            "AND json_extract(data,'$.promise_due') != ''"
        ).fetchall()
        return [RecoveryCase.model_validate_json(r["data"]) for r in rows]

    def open_cases(self) -> list[RecoveryCase]:
        rows = self.conn.execute(
            "SELECT data FROM cases WHERE status IN ('open','scheduled')"
        ).fetchall()
        return [RecoveryCase.model_validate_json(r["data"]) for r in rows]

    def all_cases(self) -> list[RecoveryCase]:
        rows = self.conn.execute("SELECT data FROM cases").fetchall()
        return [RecoveryCase.model_validate_json(r["data"]) for r in rows]

    # ---- actions -----------------------------------------------------
    def save_action(self, action: Intervention) -> None:
        self.conn.execute(
            "INSERT INTO actions (action_id,case_id,action_type,status,scheduled_at,"
            "executed_at,cost_paise,data) VALUES (?,?,?,?,?,?,?,?) "
            "ON CONFLICT(action_id) DO UPDATE SET status=excluded.status,"
            "executed_at=excluded.executed_at,data=excluded.data",
            (
                action.action_id, action.case_id, action.action_type.value,
                action.status.value, action.scheduled_at, action.executed_at,
                action.cost_paise, _dump(action),
            ),
        )
        self.conn.commit()

    def scheduled_actions(self) -> list[Intervention]:
        rows = self.conn.execute(
            "SELECT data FROM actions WHERE status='scheduled' ORDER BY scheduled_at"
        ).fetchall()
        return [Intervention.model_validate_json(r["data"]) for r in rows]

    def due_actions(self, now_iso: str) -> list[Intervention]:
        rows = self.conn.execute(
            "SELECT data FROM actions WHERE status='scheduled' AND scheduled_at<=? "
            "ORDER BY scheduled_at",
            (now_iso,),
        ).fetchall()
        return [Intervention.model_validate_json(r["data"]) for r in rows]

    def actions_for(self, case_id: str) -> list[Intervention]:
        rows = self.conn.execute(
            "SELECT data FROM actions WHERE case_id=? ORDER BY scheduled_at", (case_id,)
        ).fetchall()
        return [Intervention.model_validate_json(r["data"]) for r in rows]

    def all_actions(self) -> list[Intervention]:
        rows = self.conn.execute("SELECT data FROM actions").fetchall()
        return [Intervention.model_validate_json(r["data"]) for r in rows]

    def actions_rows(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT a.action_id, a.case_id, a.action_type, a.status, a.scheduled_at, "
            "a.executed_at, json_extract(a.data,'$.cost_paise') AS cost_paise, "
            "c.failure_class, c.group_tag, c.amount, "
            "c.status AS case_status, c.recovered_amount, c.data AS case_data, "
            "a.data AS action_data "
            "FROM actions a JOIN cases c ON c.case_id = a.case_id"
        ).fetchall()
        return [dict(r) for r in rows]

    def supersede_scheduled(self, case_id: str) -> None:
        self.conn.execute(
            "UPDATE actions SET status='superseded', data=json_set(data,'$.status','superseded') "
            "WHERE case_id=? AND status='scheduled'", (case_id,),
        )
        self.conn.commit()

    # ---- audit -------------------------------------------------------
    def append_audit(self, event: AuditEvent) -> None:
        link = chain_append(event)
        self.conn.execute(
            "INSERT INTO audit (event_id,ts,actor,event_type,case_id,payload,chain_hash,prev_hash,chain_index) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (event.event_id, event.ts, event.actor, event.event_type,
             event.case_id, json.dumps(event.payload), link.hash, link.prev_hash, link.index),
        )
        self.conn.commit()

    def verify_audit_chain(self) -> tuple[bool, int | None]:
        """Verify the hash chain integrity from database."""
        return get_audit_chain().verify()

    def get_audit_link(self, event_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT chain_hash, prev_hash, chain_index FROM audit WHERE event_id=?",
            (event_id,),
        ).fetchone()
        if row:
            return {"chain_hash": row[0], "prev_hash": row[1], "chain_index": row[2]}
        return None

    def audit_for(self, case_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM audit WHERE case_id=? ORDER BY ts", (case_id,)
        ).fetchall()
        return [
            {
                "event_id": r["event_id"], "ts": r["ts"], "actor": r["actor"],
                "event_type": r["event_type"], **json.loads(r["payload"]),
            }
            for r in rows
        ]

    def close(self) -> None:
        self.conn.close()

    # ---- webhook idempotency -------------------------------------------
    def is_event_processed(self, event_id: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM webhook_events WHERE event_id=?", (event_id,)
        ).fetchone()
        return row is not None

    def mark_event_processed(self, event_id: str, event_type: str = "") -> None:
        from datetime import datetime, timezone
        self.conn.execute(
            "INSERT OR IGNORE INTO webhook_events (event_id, processed_at, event_type) "
            "VALUES (?,?,?)",
            (event_id, datetime.now(timezone.utc).isoformat(), event_type),
        )
        self.conn.commit()
