"""SQLite reporting views and Power BI-ready CSV exports."""
from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path

VIEWS = ("v_department_summary", "v_type_summary", "v_monthly_summary", "v_open_backlog")


def export_reports(database: Path, output: Path, as_of: str, ingest_stats: dict) -> dict:
    date = datetime.fromisoformat(as_of.replace(" ", "T"))
    if date.tzinfo is not None:
        raise ValueError("Snapshot must be a local, timezone-naive date/time")
    as_of_iso = date.isoformat(timespec="seconds")
    output.mkdir(parents=True, exist_ok=True)
    views_path = Path(__file__).resolve().parents[2] / "sql" / "reporting_views.sql"
    if not views_path.is_file():
        raise FileNotFoundError(f"SQL view definitions missing: {views_path}")
    manifest = {"snapshot_as_of": as_of_iso,
                "notes": [
                    "Historical snapshot for 2024 cohorts, not the current 2026 live backlog.",
                    "Published ONTIME / OVERDUE flags apply to closed cases; missing labels are excluded from denominator.",
                    "Invalid case timelines are excluded from open/closed denominators and reported as unknown. Department comparisons are not case-mix adjusted.",
                    "Free-text descriptions, photos and street addresses are intentionally excluded.",
                ], "ingestion": ingest_stats, "exports": {}}
    with sqlite3.connect(database) as con:
        con.execute("INSERT OR REPLACE INTO settings(name,value) VALUES ('as_of',?)", (as_of_iso,))
        con.executescript(views_path.read_text(encoding="utf-8"))
        for name in VIEWS:
            cursor = con.execute(f"SELECT * FROM {name}")
            headers = [d[0] for d in cursor.description]
            dest = output / f"{name}.csv"
            count = 0
            with dest.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(headers)
                for row in cursor:
                    writer.writerow(row)
                    count += 1
            manifest["exports"][dest.name] = count
        core = con.execute("""
            SELECT COUNT(*), SUM(open_by_asof), SUM(closed_by_asof),
                   SUM(unknown_state_asof), SUM(overdue_open_by_asof), SUM(sla_evaluable), SUM(sla_met)
            FROM v_cases_asof
        """).fetchone()
        total, open_count, closed_count, unknown_count, overdue_open, sla_eligible, sla_met = core
        manifest["summary"] = {
            "requests": total, "open_backlog_asof": open_count,
            "closed_by_asof": closed_count,
            "unknown_status_asof": unknown_count,
            "overdue_open_backlog_asof": overdue_open,
            "sla_evaluable_closed": sla_eligible,
            "on_time_closed": sla_met,
            "on_time_pct_closed": round(sla_met / sla_eligible * 100, 2) if sla_eligible else None,
        }
        if open_count + closed_count + unknown_count != total:
            raise AssertionError("Open and closed case counts fail reconciliation")
    (output / "reporting_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
