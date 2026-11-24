"""
STEP 1 - Generate NovaLend's synthetic audit data
=================================================

WHAT THIS SCRIPT DOES
    Creates the "system extracts" an IT auditor would request from NovaLend
    for the audit period 1 April 2025 - 31 March 2026, and saves them as CSV
    files in 03_Data/.

    NovaLend is a FICTIONAL company. Every name, ID and number is synthetic.

    The script also plants deliberate control failures ("exceptions") in the
    data and lists them in 99_Answer_Key_SEALED/answer_key.csv. The answer key
    is only opened at the very end, to check how well the audit found them.

FILES PRODUCED (03_Data/)
    hr_employees.csv             PeopleHub HR master (joiners and leavers)
    lendcore_users.csv           LendCore user listing as at 31-Mar-2026
    access_requests.csv          ServiceDesk access request tickets
    privileged_users.csv         Privileged accounts (LendCore, NL-DB-01, NL-APP-01)
    uar_reviews.csv              Quarterly user access review log
    change_tickets.csv           ServiceDesk change tickets
    deployment_log.csv           Production deployment log (system-generated)
    sdlc_digital_onboarding.csv  Project records for LendCore Digital Onboarding
    backup_log.csv               Nightly database backup log
    restore_tests.csv            Quarterly restore test records
    batch_job_log.csv            Nightly batch job log
    incidents.csv                ServiceDesk incidents for backup / batch failures
    system_record_counts.csv     Record counts reported by each source system

HOW TO RUN (from the project folder)
    python 03_Data/generate_data.py

    Want a fresh dataset to audit "blind"? Change SEED below and re-run.
"""

import random
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker

# Let this script import audit_utils.py from the project folder
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))
from audit_utils import (AUDIT_END, AUDIT_START, ANSWER_KEY_DIR, DATA_DIR,
                         add_business_days, is_business_day)

# ---------------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------------
SEED = 2025                          # same seed = same data every time
EXTRACTION_DATE = date(2026, 5, 4)   # date the auditor received the extracts

random.seed(SEED)
Faker.seed(SEED)
fake = Faker("en_IN")                # Indian names for a Mumbai-based company

answer_key = []                      # every planted exception is recorded here


# ---------------------------------------------------------------------------
# SMALL HELPERS
# ---------------------------------------------------------------------------
def random_business_date(start, end):
    """Pick a random Monday-Friday date between start and end."""
    while True:
        d = start + timedelta(days=random.randint(0, (end - start).days))
        if is_business_day(d):
            return d


def business_days_before(d, n):
    """Return the date that is n business days BEFORE d."""
    while n > 0:
        d -= timedelta(days=1)
        if is_business_day(d):
            n -= 1
    return d


def plant(control_id, record_id, source_file, description):
    """Record a deliberately planted exception in the answer key."""
    answer_key.append({
        "exception_id": f"AK-{len(answer_key) + 1:02d}",
        "control_id": control_id,
        "record_id": record_id,
        "source_file": source_file,
        "description": description,
    })


def is_active_on(employee, d):
    """True if the employee had joined and not yet left on date d."""
    joined = employee["hire_date"] <= d
    not_left = employee["termination_date"] is None or employee["termination_date"] > d
    return joined and not_left


# ---------------------------------------------------------------------------
# 1. HR MASTER (PeopleHub)
# ---------------------------------------------------------------------------
DEPARTMENT_SIZES = {
    "Loan Operations": 240,
    "Customer Support": 150,
    "Credit Risk": 70,
    "Finance": 45,
    "Compliance": 25,
    "HR": 20,
    "IT - Application Development": 45,
    "IT - Operations": 35,
    "IT - Information Security": 12,
}

JOB_TITLES = {
    "Loan Operations": ["Loan Officer", "Senior Loan Officer"],
    "Customer Support": ["Customer Support Executive"],
    "Credit Risk": ["Credit Analyst", "Credit Approver"],
    "Finance": ["Accountant", "Finance Analyst"],
    "Compliance": ["Compliance Analyst"],
    "HR": ["HR Executive"],
    "IT - Application Development": ["Software Developer", "Senior Developer"],
    "IT - Operations": ["Systems Engineer", "Release Engineer", "Database Administrator"],
    "IT - Information Security": ["Security Analyst"],
}

# Named people from the NovaLend scenario (plus three department heads).
# (employee_id, name, department, job title, manager_id)
KEY_PEOPLE = [
    ("E1001", "Vikram Shah", "Finance", "Chief Financial Officer", ""),
    ("E1002", "Rohan Mehta", "IT - Leadership", "Head of IT", ""),
    ("E1003", "Arjun Das", "IT - Application Development", "Application Development Lead", "E1002"),
    ("E1004", "Kavita Rao", "IT - Operations", "Change Manager", "E1002"),
    ("E1005", "Priya Nair", "IT - Operations", "IT Operations Manager", "E1002"),
    ("E1006", "Farhan Sheikh", "IT - Information Security", "Information Security Officer", "E1002"),
    ("E1007", "Sneha Kulkarni", "HR", "HR Manager", ""),
    ("E1008", "Meera Iyer", "Loan Operations", "Head of Loan Operations", ""),
    ("E1009", fake.name(), "Credit Risk", "Head of Credit Risk", ""),
    ("E1010", fake.name(), "Customer Support", "Head of Customer Support", ""),
    ("E1011", fake.name(), "Compliance", "Head of Compliance", ""),
]

# Who each department's staff report to (their line manager)
DEPARTMENT_HEAD = {
    "Finance": "E1001", "IT - Application Development": "E1003",
    "IT - Operations": "E1005", "IT - Information Security": "E1006",
    "HR": "E1007", "Loan Operations": "E1008", "Credit Risk": "E1009",
    "Customer Support": "E1010", "Compliance": "E1011",
}


def make_employees():
    employees = []
    for emp_id, name, dept, title, manager in KEY_PEOPLE:
        employees.append({
            "employee_id": emp_id, "full_name": name, "department": dept,
            "job_title": title, "manager_id": manager,
            "hire_date": date(2018, 1, 8) + timedelta(days=random.randint(0, 1500)),
            "termination_date": None,
        })

    next_id = 1012
    for dept, size in DEPARTMENT_SIZES.items():
        joiners = round(size * 0.10)          # about 10% joined during the year
        for i in range(size):
            if i < joiners:
                hire = random_business_date(AUDIT_START, date(2026, 2, 27))
            else:
                hire = random_business_date(date(2016, 1, 4), date(2025, 3, 28))
            employees.append({
                "employee_id": f"E{next_id}", "full_name": fake.name(),
                "department": dept, "job_title": random.choice(JOB_TITLES[dept]),
                "manager_id": DEPARTMENT_HEAD[dept], "hire_date": hire,
                "termination_date": None,
            })
            next_id += 1

    # About 55 people left during the year (never the named key people)
    ordinary_staff = [e for e in employees if e["employee_id"] > "E1011"]
    for emp in random.sample(ordinary_staff, 55):
        earliest_exit = max(AUDIT_START, emp["hire_date"] + timedelta(days=60))
        if earliest_exit < date(2026, 3, 20):
            emp["termination_date"] = random_business_date(earliest_exit, date(2026, 3, 20))
    return employees


# ---------------------------------------------------------------------------
# 2. LENDCORE USERS + ACCESS REQUEST TICKETS
# ---------------------------------------------------------------------------
LENDCORE_ROLE_BY_DEPT = {
    "Loan Operations": "Loan Officer",
    "Credit Risk": "Credit Approver",
    "Finance": "Finance User",
    "IT - Operations": "Operations Admin",
}


def make_lendcore_users(employees):
    users, tickets = [], []
    user_no, ticket_no = 5001, 70001

    for emp in employees:
        role = LENDCORE_ROLE_BY_DEPT.get(emp["department"])
        if role is None or emp["job_title"] == "Change Manager":
            continue                          # this employee does not use LendCore

        created = add_business_days(emp["hire_date"], random.choice([0, 1]))
        if not is_business_day(emp["hire_date"]):
            created = add_business_days(emp["hire_date"], 1)

        user = {
            "user_id": f"LC{user_no}", "employee_id": emp["employee_id"],
            "username": emp["full_name"].lower().replace(" ", ".").replace("'", ""),
            "role": role, "account_created_date": created,
            "account_status": "Active", "disabled_date": None, "last_login_date": None,
        }

        # Leavers: access disabled the same day or the next business day
        if emp["termination_date"]:
            user["account_status"] = "Disabled"
            user["disabled_date"] = add_business_days(emp["termination_date"], random.choice([0, 1]))
            user["last_login_date"] = max(created, emp["termination_date"] - timedelta(days=random.randint(0, 6)))
        else:
            user["last_login_date"] = random_business_date(date(2026, 3, 9), AUDIT_END)
        users.append(user)
        user_no += 1

        # New accounts created during the year need an approved access ticket
        if AUDIT_START <= created <= AUDIT_END:
            requested = business_days_before(emp["hire_date"], random.randint(2, 6))
            approved = min(add_business_days(requested, random.choice([0, 1, 2])), created)
            manager = next(e for e in employees if e["employee_id"] == emp["manager_id"])
            tickets.append({
                "ticket_id": f"REQ-{ticket_no}", "employee_id": emp["employee_id"],
                "role_requested": role, "requested_by": "HR Onboarding (PeopleHub)",
                "requested_date": requested, "approver_id": manager["employee_id"],
                "approver_name": manager["full_name"], "approval_date": approved,
                "ticket_status": "Fulfilled",
            })
            ticket_no += 1
    return users, tickets


# ---------------------------------------------------------------------------
# 3. PRIVILEGED ACCESS LISTING (as at 31-Mar-2026)
# ---------------------------------------------------------------------------
def make_privileged_users(employees, users):
    # Long-standing IT Operations staff (hired before the audit year, still employed)
    it_ops = [e for e in employees if e["department"] == "IT - Operations"
              and e["termination_date"] is None and e["employee_id"] > "E1011"
              and e["hire_date"] < AUDIT_START]
    chosen = random.sample(it_ops, 10)
    layout = [
        ("LendCore", "Application", "System Admin", chosen[0:3]),
        ("NL-DB-01", "Database", "PostgreSQL superuser", chosen[3:5]),
        ("NL-DB-01", "Operating System", "Linux sudo (root)", chosen[5:7]),
        ("NL-APP-01", "Operating System", "Linux sudo (root)", chosen[7:10]),
    ]
    rows = []
    for system, layer, privilege, people in layout:
        for emp in people:
            rows.append({"system": system, "layer": layer, "privilege": privilege,
                         "account_name": emp["full_name"].split()[0].lower() + "_adm",
                         "employee_id": emp["employee_id"],
                         "granted_date": max(emp["hire_date"],
                                             random_business_date(date(2021, 1, 4), date(2024, 12, 20)))})
            if system == "LendCore":          # keep the LendCore user listing consistent
                for u in users:
                    if u["employee_id"] == emp["employee_id"]:
                        u["role"] = "System Admin"
    return rows


# ---------------------------------------------------------------------------
# 4. CHANGE TICKETS + PRODUCTION DEPLOYMENT LOG
# ---------------------------------------------------------------------------
COMPONENTS = {
    "Repayments": ["Fix repayment allocation rounding", "Add part-prepayment option",
                   "Correct overdue bucket display", "Update repayment receipt template"],
    "Interest Accrual": ["Adjust day-count logic for leap year", "Fix accrual for restructured loans",
                         "Improve INTEREST_ACCRUAL job logging"],
    "Loan Origination": ["Add co-applicant field", "Update credit approval limit screen",
                         "Fix PAN validation message"],
    "GL Interface": ["Add new GL code mapping", "Fix GL_INTERFACE file header format"],
    "Reports": ["New disbursement MIS report", "Fix DPD ageing report filter",
                "Add branch column to collections report"],
}
FINANCE_COMPONENTS = ("Interest Accrual", "GL Interface")


def make_changes(employees):
    developers = [e for e in employees if e["department"] == "IT - Application Development"]
    release_team = [e for e in employees if e["department"] == "IT - Operations"
                    and e["termination_date"] is None and e["employee_id"] > "E1011"
                    and e["hire_date"] < AUDIT_START][:4]
    loan_testers = [e for e in employees if e["department"] == "Loan Operations"
                    and e["job_title"] == "Senior Loan Officer"]
    finance_testers = [e for e in employees if e["department"] == "Finance"
                       and e["employee_id"] > "E1011"]

    tickets, deployments = [], []
    for n in range(152):
        change_type = "Emergency" if n % 13 == 0 else "Normal"   # 12 emergency changes
        component = random.choice(list(COMPONENTS))
        deploy_date = random_business_date(date(2025, 4, 14), date(2026, 3, 27))
        dev = random.choice([d for d in developers if is_active_on(d, deploy_date)])
        deployer = random.choice(release_team)

        if change_type == "Normal":
            approval = business_days_before(deploy_date, random.randint(1, 3))
            uat_date = business_days_before(approval, random.randint(1, 3))
            requested = business_days_before(uat_date, random.randint(5, 12))
            testers = finance_testers if component in FINANCE_COMPONENTS else loan_testers
            uat_by = random.choice([t for t in testers if is_active_on(t, uat_date)])["full_name"]
        else:  # emergency: deployed first, approved afterwards
            requested = deploy_date
            approval = add_business_days(deploy_date, random.choice([0, 1, 2]))
            uat_date, uat_by = None, "N/A - emergency change"

        change_id = f"CHG-{25001 + n}"
        tickets.append({
            "change_id": change_id, "change_type": change_type, "component": component,
            "title": random.choice(COMPONENTS[component]), "requested_date": requested,
            "developer_id": dev["employee_id"], "uat_signoff_by": uat_by, "uat_date": uat_date,
            "approved_by": "Kavita Rao", "approval_date": approval,
            "status": "Closed - Implemented",
        })
        deployments.append({
            "change_id": change_id, "component": component,
            "deployed_by": deployer["employee_id"], "environment": "PROD",
            "deployment_datetime": f"{deploy_date} {random.randint(20, 22)}:{random.choice(['00', '15', '30', '45'])}",
        })
    return tickets, deployments, developers, release_team


# ---------------------------------------------------------------------------
# 5. SDLC RECORDS - LendCore Digital Onboarding (go-live November 2025)
# ---------------------------------------------------------------------------
def make_sdlc_records():
    return [
        {"item_id": "SDLC-01", "phase": "Requirements", "item": "Business Requirements Document",
         "record_type": "Document", "approver_name": "Meera Iyer",
         "approver_role": "Head of Loan Operations (business owner)", "date": date(2025, 6, 13),
         "reference": "DO-BRD-v1.2"},
        {"item_id": "SDLC-02", "phase": "Design", "item": "Solution Design Document",
         "record_type": "Document", "approver_name": "Arjun Das",
         "approver_role": "Application Development Lead", "date": date(2025, 7, 3),
         "reference": "DO-SDD-v1.0"},
        {"item_id": "SDLC-03", "phase": "Build", "item": "Build start",
         "record_type": "Milestone", "approver_name": "", "approver_role": "",
         "date": date(2025, 7, 7), "reference": "Project plan"},
        {"item_id": "SDLC-04", "phase": "Testing", "item": "System Test Summary Report",
         "record_type": "Document", "approver_name": "Arjun Das",
         "approver_role": "Application Development Lead", "date": date(2025, 10, 24),
         "reference": "DO-STR-v1.0"},
        {"item_id": "SDLC-05", "phase": "Testing", "item": "User Acceptance Testing sign-off",
         "record_type": "Document", "approver_name": "Meera Iyer",
         "approver_role": "Head of Loan Operations (business owner)", "date": date(2025, 11, 20),
         "reference": "DO-UAT-SIGNOFF"},
        {"item_id": "SDLC-06", "phase": "Go-live", "item": "Go-live approval",
         "record_type": "Document", "approver_name": "Rohan Mehta",
         "approver_role": "Head of IT", "date": date(2025, 11, 14), "reference": "DO-GOLIVE-APPROVAL"},
        {"item_id": "SDLC-07", "phase": "Go-live", "item": "Production go-live",
         "record_type": "Milestone", "approver_name": "", "approver_role": "",
         "date": date(2025, 11, 17), "reference": "Release note DO-R1"},
        {"item_id": "SDLC-08", "phase": "Post-implementation", "item": "Post-implementation review",
         "record_type": "Document", "approver_name": "Rohan Mehta", "approver_role": "Head of IT",
         "date": date(2025, 12, 19), "reference": "DO-PIR"},
    ]


# ---------------------------------------------------------------------------
# 6. BACKUPS, BATCH JOBS AND INCIDENTS
# ---------------------------------------------------------------------------
BACKUP_FAILURE_REASONS = ["Backup storage volume full", "Network timeout to backup server",
                          "PostgreSQL lock timeout", "Backup agent service stopped"]
BATCH_FAILURE_REASONS = ["Database connection timeout", "Upstream file not received",
                         "Job server memory error", "Data validation error on 3 records"]
BATCH_JOBS = [("EOD_REPAY_POST", "23:00", "EOD"), ("INTEREST_ACCRUAL", "23:30", "INT"),
              ("GL_INTERFACE", "02:00", "GL")]


def all_days():
    d = AUDIT_START
    while d <= AUDIT_END:
        yield d
        d += timedelta(days=1)


def make_operations(release_team):
    backups, batches, incidents = [], [], []
    incident_no = 40001

    def raise_incident(run_id, category, job, run_date, reasons, delay=None):
        nonlocal incident_no
        created = add_business_days(run_date, random.choice([0, 1]) if delay is None else delay)
        incidents.append({
            "incident_id": f"INC-{incident_no}", "category": category, "related_job": job,
            "related_run_id": run_id, "created_date": created,
            "assigned_to": random.choice(release_team)["employee_id"],
            "resolved_date": add_business_days(created, random.choice([0, 1, 2])),
            "resolution": f"{random.choice(reasons)}. Job re-run completed successfully.",
            "status": "Closed",
        })
        incident_no += 1

    days = list(all_days())
    backup_failures = set(random.sample(days, 10))
    batch_failures = set(random.sample([(d, j) for d in days for j in range(3)], 14))

    for d in days:
        run_id = f"BKP-{d:%Y%m%d}"
        failed = d in backup_failures
        backups.append({"run_id": run_id, "run_date": d, "job_name": "LENDCORE_DB_FULL_BACKUP",
                        "scheduled_time": "01:00", "status": "FAILED" if failed else "SUCCESS",
                        "backup_size_gb": None if failed else round(180 + (d - AUDIT_START).days * 0.05, 1)})
        if failed:
            raise_incident(run_id, "Backup Failure", "LENDCORE_DB_FULL_BACKUP", d, BACKUP_FAILURE_REASONS)

        for j, (job, time, code) in enumerate(BATCH_JOBS):
            run_id = f"BAT-{d:%Y%m%d}-{code}"
            failed = (d, j) in batch_failures
            batches.append({"run_id": run_id, "run_date": d, "job_name": job,
                            "scheduled_time": time, "status": "FAILED" if failed else "SUCCESS"})
            if failed:
                raise_incident(run_id, "Batch Job Failure", job, d, BATCH_FAILURE_REASONS)

    restore_tests = [
        {"test_id": "RST-Q1", "quarter": "Q1", "test_date": date(2025, 6, 20),
         "backup_restored": "BKP-20250618", "performed_by": release_team[0]["employee_id"],
         "result": "Successful - row counts verified"},
        {"test_id": "RST-Q2", "quarter": "Q2", "test_date": date(2025, 9, 19),
         "backup_restored": "BKP-20250917", "performed_by": release_team[1]["employee_id"],
         "result": "Successful - row counts verified"},
        {"test_id": "RST-Q3", "quarter": "Q3", "test_date": date(2025, 12, 19),
         "backup_restored": "BKP-20251217", "performed_by": release_team[0]["employee_id"],
         "result": "Successful - row counts verified"},
        {"test_id": "RST-Q4", "quarter": "Q4", "test_date": date(2026, 3, 20),
         "backup_restored": "BKP-20260318", "performed_by": release_team[2]["employee_id"],
         "result": "Successful - row counts verified"},
    ]
    return backups, batches, incidents, restore_tests


# ---------------------------------------------------------------------------
# 7. QUARTERLY USER ACCESS REVIEWS
# ---------------------------------------------------------------------------
def make_uar_reviews():
    quarters = [("Q1", date(2025, 6, 30)), ("Q2", date(2025, 9, 30)),
                ("Q3", date(2025, 12, 31)), ("Q4", date(2026, 3, 31))]
    rows = []
    for q, q_end in quarters:
        removals = random.randint(2, 5)
        rows.append({
            "review_id": f"UAR-{q}", "quarter": q, "quarter_end": q_end,
            "review_due_date": q_end + timedelta(days=30),
            "review_completed_date": q_end + timedelta(days=random.randint(12, 26)),
            "managers_in_scope": 5, "managers_signed_off": 5,
            "removals_requested": removals, "removals_completed": removals,
            "evidence_reference": f"UAR-FY26-{q} sign-off pack",
        })
    return rows


# ---------------------------------------------------------------------------
# 8. PLANT THE EXCEPTIONS
# Each block below breaks one NovaLend rule on purpose and records it.
# ---------------------------------------------------------------------------
def plant_exceptions(employees, users, tickets, privileged, uar, changes, deployments,
                     developers, release_team, sdlc, backups, batches, incidents, restore_tests):
    emp_by_id = {e["employee_id"]: e for e in employees}

    # --- APD-01: new user access must be approved by the line manager BEFORE access ---
    in_year_tickets = random.sample(tickets, 2)
    t = in_year_tickets[0]
    user = next(u for u in users if u["employee_id"] == t["employee_id"])
    t["approval_date"] = add_business_days(user["account_created_date"], 3)
    plant("APD-01", user["user_id"], "access_requests.csv",
          "Access granted before line-manager approval (approval 3 business days after account creation).")

    t = in_year_tickets[1]
    user = next(u for u in users if u["employee_id"] == t["employee_id"])
    tickets.remove(t)
    plant("APD-01", user["user_id"], "access_requests.csv",
          "New LendCore account created with no ServiceDesk access request ticket.")

    # --- APD-02: leavers must be disabled within 1 business day ---
    leaver_users = [u for u in users if u["account_status"] == "Disabled"
                    and emp_by_id[u["employee_id"]]["department"] == "Loan Operations"
                    and emp_by_id[u["employee_id"]]["termination_date"] <= date(2025, 11, 28)]
    late1, late2, still_active = random.sample(leaver_users, 3)
    for u, days_late in ((late1, 6), (late2, 15)):
        term = emp_by_id[u["employee_id"]]["termination_date"]
        u["disabled_date"] = add_business_days(term, days_late)
        plant("APD-02", u["employee_id"], "lendcore_users.csv",
              f"Leaver's LendCore access disabled {days_late} business days after termination.")
    term = emp_by_id[still_active["employee_id"]]["termination_date"]
    still_active.update({"account_status": "Active", "disabled_date": None,
                         "last_login_date": add_business_days(term, 9)})
    plant("APD-02", still_active["employee_id"], "lendcore_users.csv",
          "Leaver's LendCore account still active at period end, with a login 9 business days after termination.")

    # --- APD-03: quarterly access review - requested removals not completed ---
    uar[2]["removals_requested"], uar[2]["removals_completed"] = 4, 2
    plant("APD-03", "UAR-Q3", "uar_reviews.csv",
          "Q3 access review: only 2 of 4 removals requested by managers were completed.")

    # --- APD-04: a developer holds the LendCore System Admin role in production ---
    dev = random.choice([d for d in developers if d["termination_date"] is None
                         and d["employee_id"] > "E1011"])
    users.append({"user_id": "LC9001", "employee_id": dev["employee_id"],
                  "username": dev["full_name"].lower().replace(" ", "."), "role": "System Admin",
                  "account_created_date": date(2024, 2, 12), "account_status": "Active",
                  "disabled_date": None, "last_login_date": date(2026, 3, 24)})
    privileged.append({"system": "LendCore", "layer": "Application", "privilege": "System Admin",
                       "account_name": dev["full_name"].split()[0].lower() + "_adm",
                       "employee_id": dev["employee_id"], "granted_date": date(2024, 2, 12)})
    plant("APD-04", dev["employee_id"], "privileged_users.csv",
          "Application developer holds the LendCore System Admin role in production.")

    # --- APD-05: generic account not linked to any employee ---
    users.append({"user_id": "LC9002", "employee_id": None, "username": "ops_shared",
                  "role": "Operations Admin", "account_created_date": date(2023, 8, 21),
                  "account_status": "Active", "disabled_date": None,
                  "last_login_date": date(2026, 3, 30)})
    plant("APD-05", "LC9002", "lendcore_users.csv",
          "Generic/shared account 'ops_shared' not mapped to any PeopleHub employee.")

    normal = [c for c in changes if c["change_type"] == "Normal"]
    picks = random.sample(normal, 3)
    deploy_of = {d["change_id"]: d for d in deployments}

    # --- PC-01: normal change deployed with no UAT evidence ---
    picks[0]["uat_signoff_by"], picks[0]["uat_date"] = None, None
    plant("PC-01", picks[0]["change_id"], "change_tickets.csv",
          "Normal change deployed with no user acceptance testing (UAT) evidence.")

    # --- PC-02: normal change approved AFTER it was deployed ---
    deploy_date = date.fromisoformat(deploy_of[picks[1]["change_id"]]["deployment_datetime"][:10])
    picks[1]["approval_date"] = add_business_days(deploy_date, 2)
    plant("PC-02", picks[1]["change_id"], "change_tickets.csv",
          "Normal change deployed to production 2 business days before Change Manager approval.")

    # --- PC-03: a developer deployed their own change to production ---
    deploy_of[picks[2]["change_id"]]["deployed_by"] = picks[2]["developer_id"]
    plant("PC-03", picks[2]["change_id"], "deployment_log.csv",
          "Change deployed to production by its own developer instead of IT Operations.")

    # --- PC-02: deployment with no change ticket at all (unauthorised change) ---
    deployments.append({"change_id": None, "component": "Interest Accrual",
                        "deployed_by": release_team[1]["employee_id"], "environment": "PROD",
                        "deployment_datetime": "2025-09-12 22:40"})
    plant("PC-02", "NO-TICKET 2025-09-12 22:40", "deployment_log.csv",
          "Production deployment to Interest Accrual with no change ticket (unauthorised change).")

    # --- PC-04: emergency change approved too late ---
    emergency = random.choice([c for c in changes if c["change_type"] == "Emergency"])
    deploy_date = date.fromisoformat(deploy_of[emergency["change_id"]]["deployment_datetime"][:10])
    emergency["approval_date"] = add_business_days(deploy_date, 6)
    plant("PC-04", emergency["change_id"], "change_tickets.csv",
          "Emergency change approved 6 business days after deployment (limit is 2).")

    # --- PD-02: UAT signed off AFTER the Digital Onboarding go-live ---
    plant("PD-02", "SDLC-05", "sdlc_digital_onboarding.csv",
          "UAT sign-off dated 20-Nov-2025, three days after go-live on 17-Nov-2025.")

    # --- CO-01: backup failures not followed up properly ---
    failed_backups = [b for b in backups if b["status"] == "FAILED"]
    no_incident, late_incident = random.sample(failed_backups, 2)
    incidents[:] = [i for i in incidents if i["related_run_id"] != no_incident["run_id"]]
    plant("CO-01", no_incident["run_id"], "incidents.csv",
          "Backup failure with no ServiceDesk incident raised.")
    for i in incidents:
        if i["related_run_id"] == late_incident["run_id"]:
            i["created_date"] = add_business_days(late_incident["run_date"], 3)
            i["resolved_date"] = add_business_days(i["created_date"], 1)
    plant("CO-01", late_incident["run_id"], "incidents.csv",
          "Backup failure incident raised 3 business days after the failure (limit is 1).")

    # --- CO-02: Q3 restore test not performed ---
    restore_tests[:] = [r for r in restore_tests if r["quarter"] != "Q3"]
    plant("CO-02", "Q3", "restore_tests.csv", "No restore test performed in Q3 (Oct-Dec 2025).")

    # --- CO-03: GL_INTERFACE failure never logged or investigated ---
    gl_runs = [b for b in batches if b["job_name"] == "GL_INTERFACE" and b["status"] == "SUCCESS"
               and date(2025, 10, 1) <= b["run_date"] <= date(2026, 1, 31)]
    gl = random.choice(gl_runs)
    gl["status"] = "FAILED"
    plant("CO-03", gl["run_id"], "batch_job_log.csv",
          "GL_INTERFACE batch failure with no incident and no evidence of investigation.")


# ---------------------------------------------------------------------------
# 9. SAVE EVERYTHING
# ---------------------------------------------------------------------------
def save(rows, file_name, sort_by=None, columns=None):
    df = pd.DataFrame(rows)
    if columns:
        df = df[columns]
    if sort_by:
        df = df.sort_values(sort_by)
    df.to_csv(DATA_DIR / file_name, index=False)
    return len(df)


def main():
    employees = make_employees()
    users, tickets = make_lendcore_users(employees)
    privileged = make_privileged_users(employees, users)
    changes, deployments, developers, release_team = make_changes(employees)
    sdlc = make_sdlc_records()
    backups, batches, incidents, restore_tests = make_operations(release_team)
    uar = make_uar_reviews()

    plant_exceptions(employees, users, tickets, privileged, uar, changes, deployments,
                     developers, release_team, sdlc, backups, batches, incidents, restore_tests)

    # The deployment log gets its IDs in date order, as a real system would
    deployments.sort(key=lambda d: d["deployment_datetime"])
    for n, d in enumerate(deployments):
        d["deployment_id"] = f"DEP-{30001 + n}"

    # Change controls are tested from the deployment log, so the answer key
    # refers to each change exception by its deployment ID.
    deployment_id_of = {d["change_id"]: d["deployment_id"] for d in deployments}
    for row in answer_key:
        if row["control_id"].startswith("PC"):
            if row["record_id"].startswith("NO-TICKET"):
                row["record_id"] = deployment_id_of[None]
            else:
                row["record_id"] = deployment_id_of[row["record_id"]]

    hr_rows = [{**e, "employment_status": "Terminated" if e["termination_date"] else "Active"}
               for e in employees]

    counts = {
        "hr_employees.csv": ("PeopleHub", save(hr_rows, "hr_employees.csv", "employee_id")),
        "lendcore_users.csv": ("LendCore", save(users, "lendcore_users.csv", "user_id")),
        "access_requests.csv": ("ServiceDesk", save(tickets, "access_requests.csv", "ticket_id")),
        "privileged_users.csv": ("LendCore / NL-DB-01 / NL-APP-01", save(privileged, "privileged_users.csv")),
        "uar_reviews.csv": ("Information Security tracker", save(uar, "uar_reviews.csv")),
        "change_tickets.csv": ("ServiceDesk", save(changes, "change_tickets.csv", "change_id")),
        "deployment_log.csv": ("LendCore release tool", save(
            deployments, "deployment_log.csv",
            columns=["deployment_id", "change_id", "component", "deployed_by",
                     "environment", "deployment_datetime"])),
        "sdlc_digital_onboarding.csv": ("Project repository", save(sdlc, "sdlc_digital_onboarding.csv")),
        "backup_log.csv": ("Backup scheduler", save(backups, "backup_log.csv")),
        "restore_tests.csv": ("IT Operations tracker", save(restore_tests, "restore_tests.csv")),
        "batch_job_log.csv": ("Job scheduler", save(batches, "batch_job_log.csv")),
        "incidents.csv": ("ServiceDesk", save(incidents, "incidents.csv", "incident_id")),
    }

    # Record counts "shown on screen" in each source system when the extract was run.
    # The auditor compares these to the files to check the extracts are complete.
    save([{"file_name": f, "source_system": s, "record_count_reported": c,
           "extracted_by": "Priya Nair (IT Operations)", "extraction_date": EXTRACTION_DATE}
          for f, (s, c) in counts.items()], "system_record_counts.csv")

    ANSWER_KEY_DIR.mkdir(exist_ok=True)
    pd.DataFrame(answer_key).to_csv(ANSWER_KEY_DIR / "answer_key.csv", index=False)

    print("Synthetic NovaLend data created in 03_Data/")
    for f, (s, c) in counts.items():
        print(f"  {f:<30} {c:>6} records")
    print(f"Answer key sealed: {len(answer_key)} planted exceptions (do not open yet)")


if __name__ == "__main__":
    main()
