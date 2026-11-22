# Metric definitions and boundaries

**Scope:** requests opened during 2024 in the official Boston 311 legacy export. The
snapshot is taken at **2024-12-31 23:59:59** (Boston local wall time). Data released
later can update a case's final status; the pipeline reconstructs historical
open/closed state using its closed date and the snapshot cutoff.

| Metric | Definition | Caveat |
| --- | --- | --- |
| Demand | Number of distinct cases opened in 2024 | No city population denominator |
| Closed by snapshot | `closed_at <= as_of` | Closure is not necessarily work completed satisfactorily |
| Open backlog as of snapshot | No closed date by cutoff, or closure after cutoff | Not today's operational backlog |
| Overdue open backlog | Open at cutoff and non-null published target date before cutoff | Depends on published targets |
| On-time closure rate | Published ONTIME closed cases / closed cases with published ONTIME/OVERDUE flag | Excludes missing flags; not independently audited |
| Average closure cycle | Mean elapsed wall-clock hours from opened to closed among valid closed cases | Can be skewed by very long cases; does not measure active processing time |
| Unknown timeline | Invalid/negative closure date or duration | Separated from open/closed status to avoid a false backlog |
| Validation exclusions | Missing/invalid case ID/open date, duplicates, wrong-year rows | Reported in manifest; not silently ignored |

**Do not** claim staffing levels, internal routing history, rework counts,
causal intervention impacts, a verified staffing bottleneck, or process
steps that are not observed in the source file. A queue is the published
category, not an event-level trajectory.

**Comparisons:** Departments receive different types of requests. A high
average processing time may reflect a different service mix. Later work
should compare within request categories and apply sample-size thresholds.

**Source and 2025 caveat:** The city began migrating the 311 backend in
October 2025 and has a separate new-system dataset. This initial project
uses 2024 to avoid accidentally treating a software transition as a
change in service performance. Source: https://data.boston.gov/dataset/311-service-requests
