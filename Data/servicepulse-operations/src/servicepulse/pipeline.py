"""Ingest public 311 CSVs into a privacy-minimized SQLite analytical table."""
from __future__ import annotations

import csv
import hashlib
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    opened_at TEXT NOT NULL,
    target_at TEXT,
    closed_at TEXT,
    source_on_time TEXT,
    source_status TEXT,
    service_type TEXT,
    department TEXT,
    queue TEXT,
    neighborhood TEXT,
    channel TEXT,
    cycle_hours REAL,
    validation_issue TEXT NOT NULL DEFAULT 'OK'
);
CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_cases_opened ON cases(opened_at);
CREATE INDEX IF NOT EXISTS ix_cases_department ON cases(department);
CREATE INDEX IF NOT EXISTS ix_cases_type ON cases(service_type);
"""

ALIASES = {
    "case_id": ("case_enquiry_id",),
    "opened_at": ("open_dt", "open_date"),
    "closed_at": ("closed_dt", "closed_date"),
    "target_at": ("target_dt", "sla_target_dt", "target_close_date"),
    "source_on_time": ("ontime", "on_time"),
    "source_status": ("case_status", "status"),
    "service_type": ("type", "service_name"),
    "department": ("department", "assigned_department"),
    "queue": ("queue", "assigned_team"),
    "neighborhood": ("neighborhood",),
    "channel": ("source",),
}
REQUIRED = ("case_id", "opened_at", "service_type")
FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%m/%d/%Y %I:%M:%S %p",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y",
    "%Y-%m-%d",
)


def parse_date(raw: str | None) -> datetime | None:
    """Return naive wall-clock datetime or None for blank dates; reject invalid strings."""
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if value.tzinfo is not None:
            raise ValueError("Timezone-aware date is unsupported without explicit normalization")
        return value
    except ValueError as exc:
        raise ValueError(f"Invalid timestamp: {raw!r}") from exc


def as_iso(value: datetime | None) -> str | None:
    return value.isoformat(timespec="seconds") if value else None


def columns_map(fieldnames: list[str] | None) -> dict[str, str | None]:
    if not fieldnames:
        raise ValueError("CSV has no header")
    actual = {name.strip().lower(): name for name in fieldnames}
    mapping = {logical: next((actual[a] for a in choices if a in actual), None)
               for logical, choices in ALIASES.items()}
    missing = [name for name in REQUIRED if mapping[name] is None]
    if missing:
        raise ValueError(f"Required columns missing: {', '.join(missing)}")
    return mapping


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ingest(input_csv: Path, database: Path, year: int = 2024) -> dict[str, int | str]:
    """Load matching-year requests, retaining only fields needed for KPI reporting."""
    if not input_csv.is_file():
        raise FileNotFoundError(f"CSV not found: {input_csv}")
    database.parent.mkdir(parents=True, exist_ok=True)
    counts: Counter[str] = Counter()
    with sqlite3.connect(database) as con:
        con.executescript(SCHEMA)
        con.execute("DELETE FROM cases")
        with input_csv.open("r", newline="", encoding="utf-8-sig", errors="replace") as stream:
            reader = csv.DictReader(stream)
            mapping = columns_map(reader.fieldnames)

            def get(row: dict[str, str], key: str) -> str:
                header = mapping.get(key)
                return (row.get(header) or "").strip() if header else ""

            for row in reader:
                counts["source_rows"] += 1
                ident = get(row, "case_id")
                if not ident:
                    counts["missing_case_id"] += 1
                    continue
                try:
                    opened = parse_date(get(row, "opened_at"))
                except ValueError:
                    counts["invalid_open_date"] += 1
                    continue
                if opened is None:
                    counts["missing_open_date"] += 1
                    continue
                if opened.year != year:
                    counts["other_year_rows"] += 1
                    continue
                issue = "OK"
                closed_raw = get(row, "closed_at")
                try:
                    closed = parse_date(closed_raw)
                except ValueError:
                    closed = None
                    issue = "INVALID_CLOSE_DATE"
                    counts["invalid_close_date"] += 1
                target_raw = get(row, "target_at")
                try:
                    target = parse_date(target_raw)
                except ValueError:
                    target = None
                    counts["invalid_target_date"] += 1
                cycle = None
                if closed is not None:
                    cycle = (closed - opened).total_seconds() / 3600.0
                    if cycle < 0:
                        issue = "NEGATIVE_CYCLE_TIME"
                        cycle = None
                        counts["negative_cycle_time"] += 1
                code = get(row, "source_on_time").upper().replace(" ", "")
                if code in ("YES", "TRUE", "ON_TIME"):
                    code = "ONTIME"
                elif code in ("NO", "FALSE", "LATE"):
                    code = "OVERDUE"
                if code not in ("ONTIME", "OVERDUE"):
                    code = None
                record = (
                    ident, as_iso(opened), as_iso(target), as_iso(closed), code,
                    get(row, "source_status") or None,
                    get(row, "service_type") or "Unknown",
                    get(row, "department") or "Unknown",
                    get(row, "queue") or "Unknown",
                    get(row, "neighborhood") or "Unknown",
                    get(row, "channel") or "Unknown", cycle, issue,
                )
                cur = con.execute("""
                    INSERT OR IGNORE INTO cases (
                        case_id, opened_at, target_at, closed_at, source_on_time,
                        source_status, service_type, department, queue, neighborhood,
                        channel, cycle_hours, validation_issue)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, record)
                if cur.rowcount == 0:
                    counts["duplicate_case_id"] += 1
                else:
                    counts["loaded_rows"] += 1
    return dict(counts) | {"source_sha256": sha256_file(input_csv), "source_name": input_csv.name}
