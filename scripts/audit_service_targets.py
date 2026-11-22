"""Audit service target windows and recorded post-snapshot closures.

Use after the ServicePulse ingestion and reporting pipeline:
    python scripts/audit_service_targets.py

The two CSV exports contain only aggregated counts; no case IDs or addresses.
The source's target/queue fields may reflect later updates rather than a
true point-in-time record of case assignment or deadline policy.
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path


def write_csv(path: Path, rows: list[sqlite3.Row]) -> None:
    if not rows:
        raise ValueError(f"No result rows for {path.name}")
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(rows[0].keys())
        writer.writerows([tuple(row) for row in rows])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit target windows and post-snapshot closure for a service type"
    )
    parser.add_argument("--db", type=Path, default=Path("build/servicepulse.sqlite"))
    parser.add_argument("--output", type=Path, default=Path("build/analysis"))
    parser.add_argument("--department", default="BTDT")
    parser.add_argument("--service", default="Parking Enforcement")
    args = parser.parse_args()

    if not args.db.is_file():
        parser.error(f"Database not found: {args.db}. Run the main pipeline first.")

    with sqlite3.connect(args.db) as con:
        con.row_factory = sqlite3.Row
        try:
            setting = con.execute(
                "SELECT value FROM settings WHERE name='as_of'"
            ).fetchone()
        except sqlite3.OperationalError:
            parser.error("ServicePulse database is missing its reporting tables.")
        if setting is None:
            parser.error("Snapshot date missing; rerun the reporting pipeline.")
        snapshot = setting["value"]
        params = (args.department, args.service)

        target_windows = con.execute(
            """
            SELECT
                CASE
                  WHEN target_at IS NULL THEN 'Missing target'
                  WHEN JULIANDAY(target_at) < JULIANDAY(opened_at) THEN 'Target before opening'
                  WHEN JULIANDAY(target_at) - JULIANDAY(opened_at) <= 1 THEN '0-1 day'
                  WHEN JULIANDAY(target_at) - JULIANDAY(opened_at) <= 3 THEN '1-3 days'
                  WHEN JULIANDAY(target_at) - JULIANDAY(opened_at) <= 7 THEN '3-7 days'
                  WHEN JULIANDAY(target_at) - JULIANDAY(opened_at) <= 30 THEN '7-30 days'
                  ELSE 'Over 30 days'
                END AS target_window,
                COUNT(*) AS requests,
                SUM(open_by_asof) AS open_at_snapshot,
                SUM(overdue_open_by_asof) AS overdue_open_at_snapshot,
                SUM(closed_by_asof) AS closed_by_snapshot,
                SUM(sla_met) AS on_time_closed
            FROM v_cases_asof
            WHERE department=? AND service_type=?
            GROUP BY target_window
            ORDER BY CASE target_window
                WHEN 'Target before opening' THEN 0
                WHEN '0-1 day' THEN 1
                WHEN '1-3 days' THEN 2
                WHEN '3-7 days' THEN 3
                WHEN '7-30 days' THEN 4
                WHEN 'Over 30 days' THEN 5
                ELSE 6 END
            """,
            params
        ).fetchall()

        closure_outcomes = con.execute(
            """
            SELECT
                CASE
                  WHEN closed_at IS NULL THEN 'No closure recorded in source'
                  WHEN closed_at > ? THEN 'Closed after 2024 snapshot (per source)'
                  ELSE 'Inconsistent closure status'
                END AS outcome,
                COUNT(*) AS open_at_snapshot,
                SUM(overdue_open_by_asof) AS overdue_open_at_snapshot
            FROM v_cases_asof
            WHERE department=? AND service_type=? AND open_by_asof=1
            GROUP BY outcome
            ORDER BY open_at_snapshot DESC
            """,
            (snapshot, *params)
        ).fetchall()

    total_requests = sum(row["requests"] for row in target_windows)
    total_open = sum(row["open_at_snapshot"] for row in target_windows)
    if total_requests == 0:
        parser.error("No matching department/service records found.")
    if sum(row["open_at_snapshot"] for row in closure_outcomes) != total_open:
        raise AssertionError("Post-snapshot closure counts do not reconcile.")

    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "service_target_windows.csv", target_windows)
    write_csv(args.output / "service_later_closures.csv", closure_outcomes)

    print(f"Snapshot: {snapshot} | {args.department} | {args.service}")
    print(f"Total requests: {total_requests:,} | Open at snapshot: {total_open:,}")
    print("\nTARGET WINDOWS (opened to recorded target):")
    for row in target_windows:
        print(f"  {row['target_window']}: requests={row['requests']:,}, "
              f"open={row['open_at_snapshot']:,}, "
              f"overdue-open={row['overdue_open_at_snapshot']:,}")
    print("\nSUBSEQUENT CLOSURE RECORDS FOR SNAPSHOT-OPEN REQUESTS:")
    for row in closure_outcomes:
        print(f"  {row['outcome']}: open={row['open_at_snapshot']:,}, "
              f"overdue={row['overdue_open_at_snapshot']:,}")

    print("\nSaved: build/analysis/service_target_windows.csv")
    print("Saved: build/analysis/service_later_closures.csv")
    print("Caution: These records do not reveal staffing, active handling time,")
    print("deadline revisions, or case assignment as of the 2024 snapshot.")


if __name__ == "__main__":
    main()
