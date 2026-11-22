# ServicePulse: Operational Performance & Process Improvement

**Real municipal service data | Python · SQLite · SQL · Power BI planned**

> How can an operations team identify which service workflows fall behind,
> determine where delays concentrate, and prioritize investigations without
> mistaking service-mix differences for performance failures?

ServicePulse analyzes real, publicly released Boston 311 service requests.
The initial baseline uses requests opened in **2024**, before the city's
October 2025 migration to an additional service-management system. The raw
CSV is downloaded by the user and is **not committed**, since it includes
street-level locations and free-text fields that are unnecessary for this
analysis.

This is a **portfolio analysis**, not a City of Boston project or an actual
process intervention. Published service flags will be evaluated critically.

## Milestones

1. **Foundation (starter implemented):** Download or import official CSV, validate dates and identifiers, load privacy-minimized SQLite table, generate SQL aggregates and a reporting manifest.
2. **Analyze:** Investigate intake demand, service-level results, category mix, queue performance, backlog and long-tail closure times. Compare similar work types rather than rank departments without adjustment.
3. **Recommend:** Build an evidence-backed prioritization framework and **labeled what-if scenarios**, not fabricated realized savings.
4. **Communicate:** Power BI executive, bottleneck and recommendation pages, plus portfolio case study.

## Data source

Publisher: **City of Boston / Analyze Boston**. Dataset: [311 Service Requests](https://data.boston.gov/dataset/311-service-requests); annual CSV: [311 Service Requests - 2024](https://data.boston.gov/dataset/8048697b-ad64-4bfc-b090-ee00169f2323/resource/dff4d804-5031-443a-8409-8344efd0e5c8/download/lagan_311_open_data_2024_rvsd3.csv).

The downloadable annual file has the case identifier, opening/closing and
target dates, source on-time label, type, department, queue, neighborhood and
intake source. The source can be updated after 2024 and its published on-time
labels are not equivalent to independently measured staffing productivity.

## Quick start (Windows PowerShell, macOS or Linux)

Requires Python 3.10+; no third-party runtime packages.

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python scripts/download_data.py
python -m servicepulse --input data/raw/boston_311_2024.csv --as-of 2024-12-31T23:59:59
```

If automated download is blocked, use the City of Boston link above and
manually save the file to `data/raw/boston_311_2024.csv`.

This will create:

- `build/servicepulse.sqlite`: trimmed analytical case table and SQL views.
- `build/reporting/v_department_summary.csv`: department KPIs and reporting denominators.
- `build/reporting/v_type_summary.csv`: service-type workload, backlog and timeliness.
- `build/reporting/v_monthly_summary.csv`: monthly opened cohorts and snapshot outcomes.
- `build/reporting/v_open_backlog.csv`: individual open cases and age at snapshot (public case IDs only).
- `build/reporting/reporting_manifest.json`: source SHA-256, exclusions, reconciliation and metric caveats.

**All reported findings must be calculated from the downloaded source.** The
tests use a tiny fictional fixture, not an assertion about 2024 real data.

## Main analytical decisions

- Use one complete year of the **legacy** backend, because 2025/2026 spans a system transition.
- For 2024 requests, reconstruct the year-end snapshot using actual close dates; later closure must not erase the historical backlog.
- Count published `ONTIME` / `OVERDUE` status only for cases closed by snapshot with a usable status flag; report denominator.
- Exclude invalid and negative cycle durations from time averages; separate anomalous timelines from both closed and open backlogs, and report validation counts.
- Do not infer rework, staffing, team handoffs, active handling time or proven causes: these are not captured by the data.
- Compare like-for-like service types before suggesting bottlenecks or interventions.

For definitions, assumptions and cautions see [metric definitions](docs/metric_definitions.md).

## Repository structure

```text
servicepulse-operations/
├── data/raw/                 # Not committed: full public exports
├── src/servicepulse/        # Validation, SQLite ingestion, reporting CLI
├── sql/reporting_views.sql  # Four reporting views + snapshot case view
├── scripts/download_data.py # Optional official CSV downloader
├── tests/                   # Regression tests using a small fictional fixture
├── docs/metric_definitions.md
└── .github/workflows/ci.yml
```

**Status:** Milestone 1 starter. No analysis results or Power BI report have been claimed yet.
