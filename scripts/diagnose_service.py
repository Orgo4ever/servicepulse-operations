"""Diagnose a department/service-type backlog using aggregate SQLite queries.

Runs against a previously generated ServicePulse SQLite database. Outputs only
aggregate queue and backlog-age tables; no case IDs or personal details.
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path


def export(path: Path, rows: list[sqlite3.Row]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        if rows:
            writer.writerow(rows[0].keys())
            writer.writerows(tuple(row) for row in rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Investigate one service type's queue and backlog patterns")
    parser.add_argument("--db", type=Path, default=Path("build/servicepulse.sqlite"))
    parser.add_argument("--department", default="BTDT")
    parser.add_argument("--service", default="Parking Enforcement")
    parser.add_argument("--output", type=Path, default=Path("build/analysis"))
    parser.add_argument("--top", type=int, default=12)
    args = parser.parse_args()

    if not args.db.is_file():
        parser.error(f"Missing SQLite database {args.db}. Run python -m servicepulse first.")
    if args.top < 1:
        parser.error("--top must be at least 1.")

    with sqlite3.connect(args.db) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT value FROM settings WHERE name='as_of'").fetchone()
        if row is None:
            parser.error("Missing as_of snapshot setting; rerun the main pipeline.")
        snapshot = row[0]

        totals = con.execute("""
            SELECT COUNT(*) AS total_requests,
                   COALESCE(SUM(open_by_asof),0) AS open_requests,
                   COALESCE(SUM(overdue_open_by_asof),0) AS overdue_open,
                   COALESCE(SUM(CASE WHEN open_by_asof=1 AND target_at IS NULL
                                     THEN 1 ELSE 0 END),0) AS open_without_target
            FROM v_cases_asof
            WHERE department=? AND service_type=?
        """, (args.department, args.service)).fetchone()

        if totals["total_requests"] == 0:
            parser.error("No matching requests. Check department code and service-type spelling.")

        queues = con.execute("""
            SELECT queue, COUNT(*) AS requests,
                   COALESCE(SUM(open_by_asof),0) AS open_requests,
                   COALESCE(SUM(overdue_open_by_asof),0) AS overdue_open,
                   ROUND(100.0*SUM(overdue_open_by_asof) /
                         NULLIF(SUM(open_by_asof),0),2) AS overdue_pct_of_open,
                   COALESCE(SUM(sla_evaluable),0) AS sla_evaluable_closed,
                   COALESCE(SUM(sla_met),0) AS on_time_closed,
                   ROUND(100.0*SUM(sla_met)/NULLIF(SUM(sla_evaluable),0),2)
                       AS on_time_pct_closed
            FROM v_cases_asof
            WHERE department=? AND service_type=?
            GROUP BY queue
            ORDER BY overdue_open DESC, open_requests DESC, requests DESC
        """, (args.department, args.service)).fetchall()

        ages = con.execute("""
            SELECT
                CASE
                  WHEN JULIANDAY(?) - JULIANDAY(opened_at) < 7 THEN '0-6 days'
                  WHEN JULIANDAY(?) - JULIANDAY(opened_at) < 30 THEN '7-29 days'
                  WHEN JULIANDAY(?) - JULIANDAY(opened_at) < 90 THEN '30-89 days'
                  ELSE '90+ days'
                END AS age_at_snapshot,
                COUNT(*) AS open_requests,
                COALESCE(SUM(overdue_open_by_asof),0) AS overdue_open,
                COALESCE(SUM(CASE WHEN target_at IS NULL THEN 1 ELSE 0 END),0)
                    AS without_target
            FROM v_cases_asof
            WHERE department=? AND service_type=? AND open_by_asof=1
            GROUP BY age_at_snapshot
            ORDER BY CASE age_at_snapshot
                WHEN '0-6 days' THEN 1
                WHEN '7-29 days' THEN 2
                WHEN '30-89 days' THEN 3
                ELSE 4 END
        """, (snapshot,snapshot,snapshot,args.department,args.service)).fetchall()

    if sum(r["requests"] for r in queues) != totals["total_requests"]:
        raise AssertionError("Queue request totals do not reconcile")
    if sum(r["open_requests"] for r in ages) != totals["open_requests"]:
        raise AssertionError("Backlog age totals do not reconcile")

    args.output.mkdir(parents=True, exist_ok=True)
    export(args.output / "service_queue_diagnostic.csv", queues)
    export(args.output / "service_backlog_age.csv", ages)

    print(f"Snapshot: {snapshot} | Department: {args.department} | Service: {args.service}")
    print(f"Requests: {totals['total_requests']:,} | Open: {totals['open_requests']:,} | "
          f"Overdue open: {totals['overdue_open']:,} | Open without target: {totals['open_without_target']:,}")
    print("\nQUEUES (sorted by overdue open requests)")
    for row in queues[:args.top]:
        print(f"  {row['queue']}: requests={row['requests']:,}, "
              f"open={row['open_requests']:,}, overdue={row['overdue_open']:,}, "
              f"closed-on-time={row['on_time_pct_closed']}%")
    print("\nBACKLOG AGE AT SNAPSHOT")
    for row in ages:
        print(f"  {row['age_at_snapshot']}: open={row['open_requests']:,}, "
              f"overdue={row['overdue_open']:,}, missing-target={row['without_target']:,}")
    print("\nSaved aggregate outputs in build/analysis/.")
    print("Age reflects calendar time since opening, not active staff handling time.")


if __name__ == "__main__":
    main()
