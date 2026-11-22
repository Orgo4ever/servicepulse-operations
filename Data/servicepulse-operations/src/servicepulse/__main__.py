"""Run the initial ServicePulse ingestion and reporting pipeline."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from servicepulse.pipeline import ingest
from servicepulse.reporting import export_reports


def main() -> None:
    p = argparse.ArgumentParser(description="Build a reproducible Boston 311 operations snapshot")
    p.add_argument("--input", type=Path, required=True, help="Official 2024 Boston 311 CSV")
    p.add_argument("--db", type=Path, default=Path("build/servicepulse.sqlite"))
    p.add_argument("--output", type=Path, default=Path("build/reporting"))
    p.add_argument("--year", type=int, default=2024)
    p.add_argument("--as-of", default="2024-12-31T23:59:59",
                   help="End-of-period snapshot; latest closure is counted only if <= cutoff")
    args = p.parse_args()
    ingestion = ingest(args.input, args.db, args.year)
    manifest = export_reports(args.db, args.output, args.as_of, ingestion)
    print(json.dumps(manifest["summary"], indent=2))
    print(f"Reports: {args.output.resolve()}")


if __name__ == "__main__":
    main()
