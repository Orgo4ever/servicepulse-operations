# ServicePulse: Milestone 2 operational findings

**Status:** Preliminary, reproducible descriptive analysis of 2024 requests, not
a causal evaluation or a formal audit of City of Boston operations.

**Dataset:** Boston 311 Service Requests (2024) CSV. Source filename:
`boston_311_2024.csv`. SHA-256:
`a3f80f43cc03e00a87fcb26bf2c66bc9ed63dc7ee349b8d3aa803ebac288502d`.
**Historical snapshot:** December 31, 2024, at 23:59:59.
**Analysis generated from:** `build/reporting` and `build/analysis` outputs,
using `python -m servicepulse`, `analyze_bottlenecks.py`,
`diagnose_service.py`, and `audit_service_targets.py`.

## Executive baseline

| Measure | Value | Interpretation |
|---|---:|---|
| 2024 requests imported | 306,756 | All rows in provided 2024 export loaded |
| Closed by snapshot | 247,842 | Historical cohort closures through 2024-12-31 |
| Open at snapshot | 58,914 | Includes cases closed later, when available |
| Open and overdue by snapshot | 33,348 | Open cases with a recorded target earlier than snapshot |
| On-time share of evaluable closed cases | 85.07% | 210,845/247,842 based on source on-time flags |
| Departments | 17 | Includes one record under the label `Test`; review before reporting |
| Service types | 170 | From the generated service-type export |

These are cohort measures. They are **not** Boston's current open-ticket
population or a forecast of future demand.

## Concentration of overdue open requests

| Department | Requests | Open at snapshot | Overdue open | On-time % among evaluable closed |
|---|---:|---:|---:|---:|
| BTDT | 81,447 | 18,951 | 17,598 | 63.69 |
| PWDx | 157,610 | 25,559 | 6,673 | 92.96 |
| INFO | 12,983 | 6,012 | 4,513 | 84.41 |
| ISD | 18,624 | 3,835 | 2,647 | 85.46 |
| BWSC | 3,406 | 1,931 | 1,319 | 79.73 |

BTDT accounts for 52.8% of all overdue open cases (17,598/33,348).
But BTDT and PWDx handle different service mixes and target windows,
so raw on-time percentages must **not** be interpreted as a ranking of
department efficiency.

## BTDT's Parking Enforcement service

| Metric | Value |
|---|---:|
| Service requests | 62,973 |
| Open at snapshot | 14,988 |
| Overdue open at snapshot | 14,854 |
| BTDT overdue backlog attributable to Parking Enforcement | 84.4% |
| Citywide overdue backlog attributable to Parking Enforcement | 44.5% |
| Reported on-time closure % | 63.32% |
| Overdue open in `BTDT_Parking Enforcement` queue | 14,813 (99.7% of Parking Enforcement overdue open) |

The backlog is highly concentrated by service and queue.
This is an **investigation priority**, not proof of a staffing shortage
or of individual worker inefficiency.

### Calendar age of Parking Enforcement cases open at snapshot

| Age from opening to 2024-12-31 | Open | Overdue open |
|---|---:|---:|
| 0–6 days | 373 | 240 |
| 7–29 days | 2,102 | 2,102 |
| 30–89 days | 5,082 | 5,082 |
| 90+ days | 7,431 | 7,430 |
| **Total** | **14,988** | **14,854** |

There were 12,513 cases open for at least 30 days (83.5% of
Parking Enforcement's snapshot-open backlog). This age measures *calendar
time since intake*, not active processing or staff workload.

### Recorded target windows

| Time between opening and recorded target | Requests | Open at snapshot | Overdue open |
|---|---:|---:|---:|
| 0–1 day | 504 | 68 | 65 |
| 1–3 days | 47,613 | 11,257 | 11,127 |
| 3–7 days | 14,855 | 3,662 | 3,662 |
| Over 30 days | 1 | 1 | 0 |
| **Total** | **62,973** | **14,988** | **14,854** |

About 99.2% of these requests had a recorded target window between one
and seven days. This suggests that service deadlines materially affect
the meaning of the overdue backlog. It does **not** establish that those
deadlines were contractual obligations or that shorter targets caused the
cases to remain open.

### Subsequent closures in the downloaded extract

Among the 14,988 Parking Enforcement requests open at the 2024 snapshot:

- 14,949 have **no closure date recorded in this extract**
  (14,821 were overdue at the snapshot).
- 39 have a recorded closure date **after** the snapshot
  (33 were overdue at the snapshot).

The extract may contain post-2024 updates, but it is not a verified live
case-status feed. Do not state that all cases with no recorded closure
date remained actively unresolved on the download date.

## Analytical boundaries and next decisions

- **Observed:** One service and one queue explain a disproportionately large
  portion of the historical overdue backlog.
- **Observed:** Many requests have short recorded target windows, while
  a large proportion of snapshot-open requests were at least 30 days old.
- **Unproven:** Staffing capacity, intervention rates, data-entry or
  case-closure policies, target-date revisions, current status and
  root causes.
- **Recommended investigation:** Confirm what constitutes a completed
  Parking Enforcement request, whether enforcement activities are routinely
  closed in the 311 system, and how target policies were defined in 2024.
- **Recommended dashboard:** Separate request volume, backlog, overdue share
  and age; preserve denominators and label the historical cutoff prominently.
- **Scenario modeling:** Model transparent hypothetical resolution rates
  later; do not report projected improvements as observed savings.

## Reproduction

From the repository root, with the official annual CSV available locally:

```bash
python -m servicepulse --input data/raw/boston_311_2024.csv --as-of 2024-12-31T23:59:59
python scripts/analyze_bottlenecks.py
python scripts/diagnose_service.py
python scripts/audit_service_targets.py
```

The reporting files are in `build/reporting` and diagnostic aggregate
files are in `build/analysis`. The raw CSV, case-level backlog export,
and SQLite database should remain local. Aggregated results can be
reviewed for publication after verifying labels and disclosure risk.

**Next steps:** Explore monthly cohorts and like-for-like comparisons
while building the Power BI executive and bottleneck pages; then
document potential process checks and explicitly hypothetical scenarios.
