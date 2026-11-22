DROP VIEW IF EXISTS v_cases_asof;
CREATE VIEW v_cases_asof AS
WITH cutoff AS (SELECT value AS at FROM settings WHERE name='as_of')
SELECT c.*,
       CASE WHEN c.validation_issue = 'OK' AND c.closed_at IS NOT NULL AND c.closed_at <= cutoff.at THEN 1 ELSE 0 END AS closed_by_asof,
       CASE WHEN c.validation_issue = 'OK' AND (c.closed_at IS NULL OR c.closed_at > cutoff.at) THEN 1 ELSE 0 END AS open_by_asof,
       CASE WHEN c.validation_issue <> 'OK' THEN 1 ELSE 0 END AS unknown_state_asof,
       CASE WHEN c.validation_issue = 'OK' AND (c.closed_at IS NULL OR c.closed_at > cutoff.at)
                 AND c.target_at IS NOT NULL AND c.target_at < cutoff.at THEN 1 ELSE 0 END AS overdue_open_by_asof,
       CASE WHEN c.closed_at IS NOT NULL AND c.closed_at <= cutoff.at
                 AND c.validation_issue = 'OK' AND c.cycle_hours IS NOT NULL
            THEN c.cycle_hours ELSE NULL END AS valid_closed_cycle_hours,
       CASE WHEN c.validation_issue = 'OK' AND c.closed_at IS NOT NULL AND c.closed_at <= cutoff.at
                 AND c.source_on_time IN ('ONTIME','OVERDUE') THEN 1 ELSE 0 END AS sla_evaluable,
       CASE WHEN c.validation_issue = 'OK' AND c.closed_at IS NOT NULL AND c.closed_at <= cutoff.at
                 AND c.source_on_time = 'ONTIME' THEN 1 ELSE 0 END AS sla_met
FROM cases c CROSS JOIN cutoff;

DROP VIEW IF EXISTS v_department_summary;
CREATE VIEW v_department_summary AS
SELECT department, COUNT(*) AS requests,
       SUM(closed_by_asof) AS closed_requests,
       SUM(open_by_asof) AS open_backlog,
       SUM(overdue_open_by_asof) AS overdue_open_backlog,
       SUM(sla_evaluable) AS sla_evaluable_closed,
       SUM(sla_met) AS on_time_closed,
       ROUND(100.0*SUM(sla_met)/NULLIF(SUM(sla_evaluable),0),2) AS on_time_pct,
       ROUND(AVG(valid_closed_cycle_hours),2) AS mean_cycle_hours
FROM v_cases_asof GROUP BY department;

DROP VIEW IF EXISTS v_type_summary;
CREATE VIEW v_type_summary AS
SELECT service_type, COUNT(*) AS requests,
       SUM(closed_by_asof) AS closed_requests,
       SUM(open_by_asof) AS open_backlog,
       SUM(overdue_open_by_asof) AS overdue_open_backlog,
       SUM(sla_evaluable) AS sla_evaluable_closed,
       SUM(sla_met) AS on_time_closed,
       ROUND(100.0*SUM(sla_met)/NULLIF(SUM(sla_evaluable),0),2) AS on_time_pct,
       ROUND(AVG(valid_closed_cycle_hours),2) AS mean_cycle_hours
FROM v_cases_asof GROUP BY service_type;

DROP VIEW IF EXISTS v_monthly_summary;
CREATE VIEW v_monthly_summary AS
SELECT SUBSTR(opened_at,1,7) AS opened_month, COUNT(*) AS requests,
       SUM(closed_by_asof) AS closed_by_snapshot,
       SUM(open_by_asof) AS open_by_snapshot,
       SUM(sla_evaluable) AS sla_evaluable_closed,
       SUM(sla_met) AS on_time_closed,
       ROUND(100.0*SUM(sla_met)/NULLIF(SUM(sla_evaluable),0),2) AS on_time_pct
FROM v_cases_asof GROUP BY SUBSTR(opened_at,1,7);

DROP VIEW IF EXISTS v_open_backlog;
CREATE VIEW v_open_backlog AS
SELECT case_id, opened_at, target_at, service_type, department, queue,
       neighborhood, overdue_open_by_asof,
       ROUND(24.0*(JULIANDAY((SELECT value FROM settings WHERE name='as_of'))-JULIANDAY(opened_at)),2) AS open_age_hours
FROM v_cases_asof WHERE open_by_asof=1;
