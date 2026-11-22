"""Produce reusable, aggregate service bottleneck exports from ServicePulse SQLite.

Run from repository root:
    python scripts/analyze_bottlenecks.py

Uses the existing 2024 snapshot settings in build/servicepulse.sqlite.
No raw addresses, case identifiers or free-text case descriptions are exported.
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path


METRICS_SQL = """
    COUNT(*) AS requests,
    COALESCE(SUM(closed_by_asof), 0) AS closed_requests,
    COALESCE(SUM(open_by_asof), 0) AS open_backlog,
    COALESCE(SUM(overdue_open_by_asof), 0) AS overdue_open_backlog,
    COALESCE(SUM(sla_evaluable), 0) AS sla_evaluable_closed,
    COALESCE(SUM(sla_met), 0) AS on_time_closed,
    ROUND(
        100.0 * SUM(sla_met) / NULLIF(SUM(sla_evaluable), 0), 2
    ) AS on_time_pct_closed
"""


def aggregate(con: sqlite3.Connection, dimension: str) -> list[sqlite3.Row]:
    """Aggregate at department + service type, or department + queue grain."""
    if dimension not in {"service_type", "queue"}:
        raise ValueError("Unsupported grouping dimension")
    sql = f"""
        SELECT department, {dimension}, {METRICS_SQL}
        FROM v_cases_asof
        GROUP BY department, {dimension}
        ORDER BY overdue_open_backlog DESC, open_backlog DESC, requests DESC
    """
    return con.execute(sql).fetchall()


def export_csv(path: Path, rows: list[sqlite3.Row]) -> None:
    if not rows:
        raise ValueError(f"No rows to export: {path.name}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(rows[0].keys())
        writer.writerows(tuple(row) for row in rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze service bottlenecks by department, type and queue")
    parser.add_argument("--db", type=Path, default=Path("build/servicepulse.sqlite"))
    parser.add_argument("--output", type=Path, default=Path("build/analysis"))
    parser.add_argument("--department", default="BTDT", help="Department to display in terminal")
    parser.add_argument("--top", type=int, default=12)
    args = parser.parse_args()

    if not args.db.is_file():
        parser.error(f"SQLite database not found: {args.db}. Run python -m servicepulse first.")
    if args.top < 1:
        parser.error("--top must be at least 1")

    args.output.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(args.db) as con:
        con.row_factory = sqlite3.Row
        snapshot_row = con.execute("SELECT value FROM settings WHERE name = 'as_of'").fetchone()
        if snapshot_row is None:
            parser.error("Snapshot cutoff is missing in settings. Run the reporting pipeline first.")
        snapshot = snapshot_row[0]

        service_rows = aggregate(con, "service_type")
        queue_rows = aggregate(con, "queue")
        totals = con.execute("""
            SELECT COUNT(*) AS requests,
                   COALESCE(SUM(open_by_asof), 0) AS open_backlog,
                   COALESCE(SUM(overdue_open_by_asof), 0) AS overdue_open_backlog
            FROM v_cases_asof
        """).fetchone()
        if sum(row["requests"] for row in service_rows) != totals["requests"]:
            raise AssertionError("Service-type totals do not reconcile with source")
        if sum(row["requests"] for row in queue_rows) != totals["requests"]:
            raise AssertionError("Queue totals do not reconcile with source")

    export_csv(args.output / "department_service_type.csv", service_rows)
    export_csv(args.output / "department_queue.csv", queue_rows)

    selected = [row for row in service_rows if row["department"].upper() == args.department.upper()]
    selected.sort(key=lambda row: (-row["overdue_open_backlog"], -row["open_backlog"]))
    print(f"Snapshot as of: {snapshot}")
    print(f"Total requests: {totals['requests']:,} | Open: {totals['open_backlog']:,} | Overdue open: {totals['overdue_open_backlog']:,}")
    print(f"\nTop {min(args.top, len(selected))} {args.department.upper()} service types by overdue open cases:")
    print(f"{'SERVICE TYPE':48} {'REQUESTS':>9} {'OPEN':>9} {'OVERDUE':>9} {'ON-TIME %':>11}")
    for row in selected[:args.top]:
        name = row["service_type"] or "Unknown"
        if len(name) > 47:
            name = name[:44] + "..."
        on_time = "n/a" if row["on_time_pct_closed"] is None else f"{row['on_time_pct_closed']:.2f}"
        print(f"{name:48} {row['requests']:>9,} {row['open_backlog']:>9,} {row['overdue_open_backlog']:>9,} {on_time:>11}")
    if not selected:
        print("No matching department was found; check its exact code.")

    print(f"\nCreated: {args.output / 'department_service_type.csv'}")
    print(f"Created: {args.output / 'department_queue.csv'}")
    print("These are aggregate reports; review service/queue names before external publication.")


if __name__ == "__main__":
    main()
