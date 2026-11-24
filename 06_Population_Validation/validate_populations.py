"""
STEP 2 - Validate the data and build audit populations (SQLite + SQL)
=====================================================================

WHY THIS STEP EXISTS
    Before sampling, an auditor must be confident the data is COMPLETE
    (nothing missing) and ACCURATE (not altered or broken). A sample drawn
    from an incomplete population proves nothing. System reports used as
    audit evidence are called IPE - "Information Produced by the Entity".

WHAT THIS SCRIPT DOES
    1. Loads every CSV from 03_Data/ into a SQLite database (novalend_audit.db).
    2. Runs completeness and accuracy checks with SQL:
         A. Record counts agree to the counts reported by each source system
         B. No duplicate key values (e.g. the same ticket ID twice)
         C. Mandatory fields are not blank
         D. Daily logs cover every day of the audit period
         E. Deployment log reconciled to change tickets (both directions)
    3. Builds one population per control with SQL queries (JOINs) and saves
       them to 06_Population_Validation/populations/.
    4. Writes the workpaper Population_Validation_Workpaper.xlsx.

HOW TO RUN (from the project folder)
    python 06_Population_Validation/validate_populations.py
"""

import sqlite3
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))
from audit_utils import (AUDIT_END, AUDIT_START, DATA_DIR, POPULATION_DIR,
                         VALIDATION_DIR, write_excel)

DB_PATH = VALIDATION_DIR / "novalend_audit.db"
START, END = str(AUDIT_START), str(AUDIT_END)

# Key column for each table (used for the duplicate check) and mandatory fields
TABLE_RULES = {
    "hr_employees": ("employee_id", ["full_name", "department", "hire_date"]),
    "lendcore_users": ("user_id", ["username", "role", "account_created_date", "account_status"]),
    "access_requests": ("ticket_id", ["employee_id", "approver_id", "approval_date"]),
    "change_tickets": ("change_id", ["change_type", "approved_by", "approval_date"]),
    "deployment_log": ("deployment_id", ["deployed_by", "deployment_datetime"]),
    "backup_log": ("run_id", ["run_date", "status"]),
    "batch_job_log": ("run_id", ["run_date", "job_name", "status"]),
    "incidents": ("incident_id", ["related_run_id", "created_date"]),
}


def run_query(conn, sql):
    """Run a SQL query and return the result as a pandas DataFrame."""
    return pd.read_sql_query(sql, conn)


# ---------------------------------------------------------------------------
# 1. LOAD THE CSV FILES INTO SQLITE
# ---------------------------------------------------------------------------
def load_database():
    if DB_PATH.exists():
        DB_PATH.unlink()                       # start fresh every run
    conn = sqlite3.connect(DB_PATH)
    for csv_file in sorted(DATA_DIR.glob("*.csv")):
        df = pd.read_csv(csv_file, dtype=str)  # read everything as text, like a raw extract
        df.to_sql(csv_file.stem, conn, index=False)
    return conn


# ---------------------------------------------------------------------------
# 2. COMPLETENESS AND ACCURACY CHECKS
# ---------------------------------------------------------------------------
def check_record_counts(conn):
    """Check A: rows in each file = record count shown in the source system."""
    rows = []
    reported = run_query(conn, "SELECT file_name, source_system, record_count_reported FROM system_record_counts")
    for _, r in reported.iterrows():
        table = r["file_name"].replace(".csv", "")
        actual = run_query(conn, f"SELECT COUNT(*) AS n FROM {table}")["n"][0]
        expected = int(r["record_count_reported"])
        rows.append({"File": r["file_name"], "Source system": r["source_system"],
                     "Count reported by system": expected, "Rows in extract": actual,
                     "Difference": actual - expected,
                     "Result": "Agreed" if actual == expected else "DIFFERENCE - investigate"})
    return pd.DataFrame(rows)


def check_duplicates(conn):
    """Check B: no key value appears more than once."""
    rows = []
    for table, (key, _) in TABLE_RULES.items():
        dupes = run_query(conn, f"""
            SELECT {key}, COUNT(*) AS times FROM {table}
            GROUP BY {key} HAVING COUNT(*) > 1""")
        rows.append({"Table": table, "Key column": key, "Duplicate keys found": len(dupes),
                     "Result": "No duplicates" if dupes.empty else "DUPLICATES - investigate"})
    return pd.DataFrame(rows)


def check_mandatory_fields(conn):
    """Check C: important fields are never blank."""
    rows = []
    for table, (_, fields) in TABLE_RULES.items():
        for field in fields:
            blanks = run_query(conn, f"SELECT COUNT(*) AS n FROM {table} WHERE {field} IS NULL OR {field} = ''")["n"][0]
            rows.append({"Table": table, "Field": field, "Blank values": blanks,
                         "Result": "Complete" if blanks == 0 else "BLANKS - follow up"})
    return pd.DataFrame(rows)


def check_date_coverage(conn):
    """Check D: daily jobs have a log entry for every day of the year (365 days)."""
    expected_days = (AUDIT_END - AUDIT_START).days + 1
    rows = []
    for table, jobs in (("backup_log", 1), ("batch_job_log", 3)):
        result = run_query(conn, f"""
            SELECT COUNT(DISTINCT run_date) AS days, COUNT(*) AS runs,
                   MIN(run_date) AS first_day, MAX(run_date) AS last_day
            FROM {table} WHERE run_date BETWEEN '{START}' AND '{END}'""").iloc[0]
        ok = result["days"] == expected_days and result["runs"] == expected_days * jobs
        rows.append({"Log": table, "Days expected": expected_days, "Days found": result["days"],
                     "Runs expected": expected_days * jobs, "Runs found": result["runs"],
                     "First day": result["first_day"], "Last day": result["last_day"],
                     "Result": "Complete" if ok else "GAPS - investigate"})
    return pd.DataFrame(rows)


def reconcile_deployments(conn):
    """
    Check E: the deployment log is system-generated, so it is the most complete
    record of what actually reached production. Every deployment should have a
    ticket, and every implemented ticket should appear in the log.
    """
    no_ticket = run_query(conn, """
        SELECT d.deployment_id, d.deployment_datetime, d.component, d.deployed_by,
               'Deployment with no change ticket' AS issue
        FROM deployment_log d
        LEFT JOIN change_tickets c ON d.change_id = c.change_id
        WHERE c.change_id IS NULL""")
    no_deployment = run_query(conn, """
        SELECT c.change_id AS deployment_id, c.approval_date AS deployment_datetime,
               c.component, '' AS deployed_by, 'Implemented ticket missing from deployment log' AS issue
        FROM change_tickets c
        LEFT JOIN deployment_log d ON c.change_id = d.change_id
        WHERE d.deployment_id IS NULL AND c.status = 'Closed - Implemented'""")
    return pd.concat([no_ticket, no_deployment], ignore_index=True)


# ---------------------------------------------------------------------------
# 3. BUILD ONE POPULATION PER CONTROL
# (control, file name, description, SQL query)
# ---------------------------------------------------------------------------
POPULATIONS = [
    ("APD-01", "APD-01_new_users.csv",
     "LendCore accounts created during the audit period, joined to HR and access tickets",
     f"""SELECT u.user_id, u.employee_id, e.full_name, e.department, u.role,
                u.account_created_date, e.manager_id,
                r.ticket_id, r.role_requested, r.approver_id, r.approver_name, r.approval_date
         FROM lendcore_users u
         LEFT JOIN hr_employees e    ON u.employee_id = e.employee_id
         LEFT JOIN access_requests r ON u.employee_id = r.employee_id
         WHERE u.account_created_date BETWEEN '{START}' AND '{END}'
         ORDER BY u.account_created_date"""),

    ("APD-02", "APD-02_leavers.csv",
     "Employees who left during the audit period and had a LendCore account",
     f"""SELECT e.employee_id, e.full_name, e.department, e.termination_date,
                u.user_id, u.account_status, u.disabled_date, u.last_login_date
         FROM hr_employees e
         JOIN lendcore_users u ON e.employee_id = u.employee_id
         WHERE e.termination_date BETWEEN '{START}' AND '{END}'
         ORDER BY e.termination_date"""),

    ("APD-03", "APD-03_uar_reviews.csv",
     "Quarterly LendCore user access reviews for Q1-Q4",
     "SELECT * FROM uar_reviews ORDER BY quarter"),

    ("APD-04", "APD-04_privileged_users.csv",
     "Privileged accounts on LendCore, NL-DB-01 and NL-APP-01 at 31-Mar-2026, joined to HR",
     """SELECT p.*, e.full_name, e.department, e.job_title, e.employment_status
        FROM privileged_users p
        LEFT JOIN hr_employees e ON p.employee_id = e.employee_id
        ORDER BY p.system, p.layer"""),

    ("APD-05", "APD-05_user_listing.csv",
     "Complete LendCore user listing at 31-Mar-2026, joined to HR",
     """SELECT u.user_id, u.username, u.role, u.account_status, u.employee_id,
               e.full_name, e.employment_status
        FROM lendcore_users u
        LEFT JOIN hr_employees e ON u.employee_id = e.employee_id
        ORDER BY u.user_id"""),

    ("PC-01/02/03", "PC_normal_deployments.csv",
     "Production deployments that were normal changes or had no ticket (source: deployment log)",
     """SELECT d.deployment_id, d.deployment_datetime, d.component, d.change_id, c.change_type,
               c.title, c.developer_id, c.uat_signoff_by, c.uat_date, c.approved_by,
               c.approval_date, d.deployed_by, e.department AS deployer_department
        FROM deployment_log d
        LEFT JOIN change_tickets c ON d.change_id = c.change_id
        LEFT JOIN hr_employees e   ON d.deployed_by = e.employee_id
        WHERE c.change_type = 'Normal' OR c.change_id IS NULL
        ORDER BY d.deployment_datetime"""),

    ("PC-04", "PC_emergency_deployments.csv",
     "Production deployments recorded as emergency changes",
     """SELECT d.deployment_id, d.deployment_datetime, d.component, d.change_id, c.title,
               c.approved_by, c.approval_date, d.deployed_by
        FROM deployment_log d
        JOIN change_tickets c ON d.change_id = c.change_id
        WHERE c.change_type = 'Emergency'
        ORDER BY d.deployment_datetime"""),

    ("PD-01/02/03", "PD_digital_onboarding.csv",
     "All project records for LendCore Digital Onboarding (one project, go-live Nov 2025)",
     "SELECT * FROM sdlc_digital_onboarding ORDER BY item_id"),

    ("CO-01", "CO-01_backup_failures.csv",
     "Failed nightly backups, joined to ServiceDesk incidents",
     """SELECT b.run_id, b.run_date, b.status, i.incident_id, i.created_date,
               i.resolved_date, i.resolution
        FROM backup_log b
        LEFT JOIN incidents i ON i.related_run_id = b.run_id
        WHERE b.status = 'FAILED'
        ORDER BY b.run_date"""),

    ("CO-02", "CO-02_restore_tests.csv",
     "Expected quarterly restore tests (Q1-Q4) matched to restore test records",
     """WITH expected(quarter) AS (VALUES ('Q1'), ('Q2'), ('Q3'), ('Q4'))
        SELECT x.quarter, r.test_id, r.test_date, r.backup_restored, r.performed_by, r.result
        FROM expected x
        LEFT JOIN restore_tests r ON x.quarter = r.quarter
        ORDER BY x.quarter"""),

    ("CO-03", "CO-03_batch_failures.csv",
     "Failed nightly batch jobs, joined to ServiceDesk incidents",
     """SELECT b.run_id, b.run_date, b.job_name, b.status, i.incident_id, i.created_date,
               i.resolved_date, i.resolution
        FROM batch_job_log b
        LEFT JOIN incidents i ON i.related_run_id = b.run_id
        WHERE b.status = 'FAILED'
        ORDER BY b.run_date"""),
]


def build_populations(conn):
    POPULATION_DIR.mkdir(exist_ok=True)
    summary = []
    for control, file_name, description, sql in POPULATIONS:
        df = run_query(conn, sql)
        df.to_csv(POPULATION_DIR / file_name, index=False)
        summary.append({"Control": control, "Population file": f"populations/{file_name}",
                        "Population definition": description, "Records": len(df),
                        "SQL used": " ".join(sql.split())})
    return pd.DataFrame(summary)


# ---------------------------------------------------------------------------
# 4. MAIN
# ---------------------------------------------------------------------------
def main():
    conn = load_database()
    counts = check_record_counts(conn)
    dupes = check_duplicates(conn)
    blanks = check_mandatory_fields(conn)
    coverage = check_date_coverage(conn)
    recon = reconcile_deployments(conn)
    populations = build_populations(conn)
    conn.close()

    summary = pd.DataFrame([
        {"Check": "A. Record counts agree to source systems",
         "Result": "Pass" if (counts["Difference"] == 0).all() else "Exception",
         "Conclusion": f"{(counts['Difference'] == 0).sum()} of {len(counts)} extracts agree to the count reported by the source system."},
        {"Check": "B. No duplicate keys",
         "Result": "Pass" if (dupes["Duplicate keys found"] == 0).all() else "Exception",
         "Conclusion": "No duplicate record IDs in any extract." if (dupes["Duplicate keys found"] == 0).all()
         else "Duplicate IDs found - see Duplicates sheet."},
        {"Check": "C. Mandatory fields complete",
         "Result": "Pass" if (blanks["Blank values"] == 0).all() else "Exception",
         "Conclusion": "All mandatory fields populated." if (blanks["Blank values"] == 0).all()
         else "Blank mandatory fields found - see Mandatory_Fields sheet."},
        {"Check": "D. Daily logs cover the full period",
         "Result": "Pass" if (coverage["Result"] == "Complete").all() else "Exception",
         "Conclusion": "Backup and batch logs contain one run per job for every day from 1-Apr-2025 to 31-Mar-2026."},
        {"Check": "E. Deployment log reconciled to change tickets",
         "Result": "Pass" if recon.empty else "Exception noted",
         "Conclusion": f"{len(recon)} reconciling item(s). Deployments with no ticket are kept IN the change population "
                       "and tested, because the deployment log (not the ticket list) is the complete record of production changes."},
    ])

    notes = pd.DataFrame({"Notes": [
        "Purpose: confirm the populations used for sampling are complete and accurate (IPE testing).",
        f"Audit period: {START} to {END}. Extracts received {pd.read_csv(DATA_DIR / 'system_record_counts.csv')['extraction_date'][0]} from IT Operations.",
        "Simplification: in a real audit the auditor would also observe the extract being run or re-perform the report query. "
        "Here, record counts reported by each system stand in for that evidence.",
        "Prepared by: Manjit Mandal  |  Reviewed by: Pending",
    ]})

    write_excel(VALIDATION_DIR / "Population_Validation_Workpaper.xlsx", {
        "Summary": summary, "A_Record_Counts": counts, "B_Duplicates": dupes,
        "C_Mandatory_Fields": blanks, "D_Date_Coverage": coverage,
        "E_Deploy_vs_Ticket": recon, "Populations": populations, "Notes": notes,
    })

    print("Population validation complete -> 06_Population_Validation/Population_Validation_Workpaper.xlsx")
    print(summary[["Check", "Result"]].to_string(index=False))
    print("\nPopulations built:")
    print(populations[["Control", "Records"]].to_string(index=False))


if __name__ == "__main__":
    main()
