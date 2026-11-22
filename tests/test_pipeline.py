from pathlib import Path
from tempfile import TemporaryDirectory
import csv
import unittest

from servicepulse.pipeline import ingest, parse_date
from servicepulse.reporting import export_reports


class PipelineTests(unittest.TestCase):
    def test_invalid_timestamp(self):
        with self.assertRaises(ValueError):
            parse_date("not-a-date")

    def test_end_to_end_fixture(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "input.csv"
            rows = [
                # Closed in 2024; on time.
                ["A", "2024-01-01 08:00:00", "2024-01-03 00:00:00", "2024-01-02 08:00:00", "ONTIME", "Closed", "Type X", "Dept 1"],
                # Still open at year end.
                ["B", "2024-02-01 08:00:00", "2024-02-03 00:00:00", "", "OVERDUE", "Open", "Type X", "Dept 1"],
                # Actually closed in 2025, but open in historical snapshot.
                ["C", "2024-11-01 08:00:00", "2024-11-05 00:00:00", "2025-01-02 08:00:00", "OVERDUE", "Closed", "Type Y", "Dept 2"],
                # Invalid cycle time should not contaminate averages.
                ["D", "2024-08-02 08:00:00", "2024-08-06 08:00:00", "2024-08-01 08:00:00", "OVERDUE", "Closed", "Type Y", "Dept 2"],
                # Duplicate ID should not add a case.
                ["A", "2024-01-01 08:00:00", "2024-01-03 00:00:00", "2024-01-02 08:00:00", "ONTIME", "Closed", "Type X", "Dept 1"],
                # Out-of-year source row excluded.
                ["E", "2023-01-01 08:00:00", "2023-01-03 00:00:00", "2023-01-02 08:00:00", "ONTIME", "Closed", "Type X", "Dept 1"],
            ]
            with source.open("w", newline="") as fp:
                w = csv.writer(fp)
                w.writerow(["case_enquiry_id", "open_dt", "target_dt", "closed_dt", "ontime", "case_status", "type", "department"])
                w.writerows(rows)
            db = base / "out.sqlite"
            stats = ingest(source, db, 2024)
            self.assertEqual(stats["loaded_rows"], 4)
            self.assertEqual(stats["duplicate_case_id"], 1)
            self.assertEqual(stats["negative_cycle_time"], 1)
            report = export_reports(db, base / "reporting", "2024-12-31T23:59:59", stats)
            self.assertEqual(report["summary"]["requests"], 4)
            self.assertEqual(report["summary"]["closed_by_asof"], 1)
            self.assertEqual(report["summary"]["unknown_status_asof"], 1)
            self.assertEqual(report["summary"]["open_backlog_asof"], 2)
            self.assertEqual(report["summary"]["overdue_open_backlog_asof"], 2)
            self.assertEqual(report["summary"]["on_time_closed"], 1)
            self.assertEqual(report["summary"]["on_time_pct_closed"], 100.0)
            self.assertTrue((base / "reporting" / "v_department_summary.csv").exists())


if __name__ == "__main__":
    unittest.main()
