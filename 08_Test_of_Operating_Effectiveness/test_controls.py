"""
STEP 4 - Test of Operating Effectiveness (ToE) + full-population analytics
==========================================================================

WHAT IS A TEST OF OPERATING EFFECTIVENESS?
    Test of Design asks "would this control work if it ran as described?".
    Test of Operating Effectiveness asks "did it actually work, every time,
    throughout the year?". We answer it by checking each sampled item against
    the control's ATTRIBUTES - the specific things that must be true.
    Example for leavers: (A) account disabled, (B) within 1 business day,
    (C) no login after the leaving date.

TWO WAYS OF TESTING IN THIS SCRIPT
    1. Sample testing   - the attribute tests are run on the SAMPLE selected in
                          step 3. This is the traditional audit approach and
                          gives the formal ToE conclusion.
    2. Data analytics   - the SAME tests are run on the WHOLE population, for
                          controls where only a sample was tested. This shows
                          how many exceptions sampling alone would have missed.

    Each test function below works on any table of records, so the logic is
    written once and used for both.

OUTPUT
    08_Test_of_Operating_Effectiveness/ToE_Workpaper.xlsx
    08_Test_of_Operating_Effectiveness/exceptions_detected.csv

HOW TO RUN (from the project folder)
    python 08_Test_of_Operating_Effectiveness/test_controls.py
"""

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))
from audit_utils import (POPULATION_DIR, SAMPLE_DIR, TESTING_DIR,
                         business_days_between, to_date, write_excel)


def has_value(value):
    """True if a field is filled in (not blank)."""
    return pd.notna(value) and str(value).strip() != ""


def result_row(record_id, checks):
    """
    Turn a set of attribute checks into one workpaper row.
    checks = {"A. Attribute name": (passed, note_if_failed)}
      passed = True / False, or None when the attribute does not apply (N/A)
    """
    row = {"Record ID": record_id}
    failures = []
    for attribute, (passed, note) in checks.items():
        if passed is None:
            row[attribute] = "N/A"
        elif passed:
            row[attribute] = "Pass"
        else:
            row[attribute] = "FAIL"
            failures.append(note)
    if all(passed is None for passed, _ in checks.values()):
        row["Result"], row["Comment"] = "Not applicable", "; ".join(n for _, n in checks.values())
    elif failures:
        row["Result"], row["Comment"] = "Exception", "; ".join(failures)
    else:
        row["Result"], row["Comment"] = "Pass", "No exception noted"
    return row


def deployment_date(row):
    return to_date(row["deployment_datetime"][:10])


# ===========================================================================
# ACCESS TO PROGRAMS AND DATA
# ===========================================================================
def test_apd01(df):
    """APD-01 New LendCore access is approved by the line manager before it is granted."""
    rows = []
    for _, r in df.iterrows():
        created, approved = to_date(r["account_created_date"]), to_date(r["approval_date"])
        ticket = has_value(r["ticket_id"])
        rows.append(result_row(r["user_id"], {
            "A. Access request ticket exists": (ticket, "No access request ticket"),
            "B. Approved by line manager": (r["approver_id"] == r["manager_id"] if ticket else None,
                                            f"Approved by {r['approver_name']}, not the line manager"),
            "C. Approved on or before access granted": (approved <= created if ticket else None,
                                                        f"Approved {approved}, access granted {created}"),
            "D. Role granted matches request": (r["role"] == r["role_requested"] if ticket else None,
                                                f"Granted {r['role']} but requested {r['role_requested']}"),
        }))
    return pd.DataFrame(rows)


def test_apd02(df):
    """APD-02 Leavers' LendCore access is disabled within 1 business day of termination."""
    rows = []
    for _, r in df.iterrows():
        term, disabled = to_date(r["termination_date"]), to_date(r["disabled_date"])
        last_login = to_date(r["last_login_date"])
        days = business_days_between(term, disabled) if disabled else None
        rows.append(result_row(r["employee_id"], {
            "A. Account disabled": (r["account_status"] == "Disabled",
                                    f"Account still active at period end (left {term})"),
            "B. Disabled within 1 business day": (days <= 1 if disabled else None,
                                                  f"Disabled {days} business days after termination"),
            "C. No login after termination": (last_login <= term,
                                              f"Last login {last_login} is after termination {term}"),
        }))
    return pd.DataFrame(rows)


def test_apd03(df):
    """APD-03 Quarterly user access review is completed, signed off and acted on."""
    rows = []
    for _, r in df.iterrows():
        rows.append(result_row(r["review_id"], {
            "A. Completed by due date": (to_date(r["review_completed_date"]) <= to_date(r["review_due_date"]),
                                         f"Completed {r['review_completed_date']}, due {r['review_due_date']}"),
            "B. All managers signed off": (r["managers_signed_off"] == r["managers_in_scope"],
                                           f"{r['managers_signed_off']} of {r['managers_in_scope']} managers signed off"),
            "C. All requested removals completed": (r["removals_completed"] == r["removals_requested"],
                                                    f"Only {r['removals_completed']} of {r['removals_requested']} requested removals completed"),
        }))
    return pd.DataFrame(rows)


def test_apd04(df):
    """APD-04 Privileged access is restricted to IT Operations staff."""
    rows = []
    for _, r in df.iterrows():
        rows.append(result_row(r["employee_id"], {
            "A. Holder is in IT Operations": (r["department"] == "IT - Operations",
                                              f"{r['privilege']} on {r['system']} held by {r['department']} ({r['job_title']})"),
            "B. Holder is a current employee": (r["employment_status"] == "Active",
                                                "Privileged account belongs to a leaver"),
        }))
    return pd.DataFrame(rows)


def test_apd05(df):
    """APD-05 Every LendCore account belongs to a named employee (no generic accounts)."""
    rows = []
    for _, r in df.iterrows():
        rows.append(result_row(r["user_id"], {
            "A. Account mapped to a PeopleHub employee": (has_value(r["full_name"]),
                                                          f"Account '{r['username']}' has no matching employee"),
        }))
    return pd.DataFrame(rows)


# ===========================================================================
# PROGRAM CHANGE (one sample of deployments is tested for PC-01, 02 and 03)
# ===========================================================================
def test_pc01(df):
    """PC-01 Normal changes are user-acceptance tested before deployment."""
    rows = []
    for _, r in df.iterrows():
        ticket = has_value(r["change_id"])
        uat_done = has_value(r["uat_signoff_by"])
        uat_date = to_date(r["uat_date"])
        rows.append(result_row(r["deployment_id"], {
            "A. UAT sign-off recorded": (uat_done if ticket else None,
                                         "No UAT evidence on the change ticket" if ticket else "No change ticket - reported under PC-02"),
            "B. UAT completed before deployment": (uat_date <= deployment_date(r) if (ticket and uat_done) else None,
                                                   f"UAT {uat_date} after deployment"),
        }))
    return pd.DataFrame(rows)


def test_pc02(df):
    """PC-02 Changes are approved by the Change Manager before deployment."""
    rows = []
    for _, r in df.iterrows():
        ticket = has_value(r["change_id"])
        approved = to_date(r["approval_date"])
        rows.append(result_row(r["deployment_id"], {
            "A. Change ticket exists": (ticket, "Deployed to production with no change ticket"),
            "B. Approved by Change Manager": (r["approved_by"] == "Kavita Rao" if ticket else None,
                                              f"Approved by {r['approved_by']}"),
            "C. Approved on or before deployment": (approved <= deployment_date(r) if ticket else None,
                                                    f"Deployed {deployment_date(r)}, approved {approved}"),
        }))
    return pd.DataFrame(rows)


def test_pc03(df):
    """PC-03 Only IT Operations deploys to production; developers cannot deploy."""
    rows = []
    for _, r in df.iterrows():
        rows.append(result_row(r["deployment_id"], {
            "A. Deployed by IT Operations": (r["deployer_department"] == "IT - Operations",
                                             f"Deployed by {r['deployed_by']} ({r['deployer_department']})"),
            "B. Deployer is not the developer": (r["deployed_by"] != r["developer_id"] if has_value(r["developer_id"]) else None,
                                                 "Developer deployed their own change"),
        }))
    return pd.DataFrame(rows)


def test_pc04(df):
    """PC-04 Emergency changes are approved within 2 business days of deployment."""
    rows = []
    for _, r in df.iterrows():
        days = business_days_between(deployment_date(r), to_date(r["approval_date"]))
        rows.append(result_row(r["deployment_id"], {
            "A. Approved by Change Manager": (r["approved_by"] == "Kavita Rao", f"Approved by {r['approved_by']}"),
            "B. Approved within 2 business days": (days <= 2, f"Approved {days} business days after deployment"),
        }))
    return pd.DataFrame(rows)


# ===========================================================================
# PROGRAM DEVELOPMENT (LendCore Digital Onboarding project)
# ===========================================================================
def project_item(df, item_id):
    return df[df["item_id"] == item_id].iloc[0]


def test_pd01(df):
    """PD-01 Business requirements approved by the business owner before build starts."""
    brd, build = project_item(df, "SDLC-01"), project_item(df, "SDLC-03")
    return pd.DataFrame([result_row("SDLC-01", {
        "A. Approved by business owner": ("business owner" in brd["approver_role"], "Not approved by business owner"),
        "B. Approved on or before build start": (to_date(brd["date"]) <= to_date(build["date"]),
                                                 f"BRD approved {brd['date']}, build started {build['date']}"),
    })])


def test_pd02(df):
    """PD-02 User acceptance testing signed off by the business owner before go-live."""
    uat, golive = project_item(df, "SDLC-05"), project_item(df, "SDLC-07")
    return pd.DataFrame([result_row("SDLC-05", {
        "A. Signed off by business owner": ("business owner" in uat["approver_role"], "UAT not signed off by business owner"),
        "B. Signed off before go-live": (to_date(uat["date"]) < to_date(golive["date"]),
                                         f"UAT signed off {uat['date']}, after go-live on {golive['date']}"),
    })])


def test_pd03(df):
    """PD-03 Go-live approved by the Head of IT before production go-live."""
    approval, golive = project_item(df, "SDLC-06"), project_item(df, "SDLC-07")
    return pd.DataFrame([result_row("SDLC-06", {
        "A. Approved by Head of IT": (approval["approver_role"] == "Head of IT", "Not approved by Head of IT"),
        "B. Approved on or before go-live": (to_date(approval["date"]) <= to_date(golive["date"]),
                                             f"Approved {approval['date']}, go-live {golive['date']}"),
    })])


# ===========================================================================
# COMPUTER OPERATIONS
# ===========================================================================
def test_co01(df):
    """CO-01 Backup failures get a ServiceDesk incident within 1 business day and are resolved."""
    rows = []
    for _, r in df.iterrows():
        incident = has_value(r["incident_id"])
        days = business_days_between(to_date(r["run_date"]), to_date(r["created_date"])) if incident else None
        rows.append(result_row(r["run_id"], {
            "A. Incident raised": (incident, "No incident raised for the backup failure"),
            "B. Raised within 1 business day": (days <= 1 if incident else None,
                                                f"Incident raised {days} business days after failure"),
            "C. Incident resolved (backup re-run)": (has_value(r["resolved_date"]) if incident else None,
                                                     "Incident not resolved"),
        }))
    return pd.DataFrame(rows)


def test_co02(df):
    """CO-02 A restore test is performed and successful every quarter."""
    rows = []
    for _, r in df.iterrows():
        performed = has_value(r["test_id"])
        rows.append(result_row(r["quarter"], {
            "A. Restore test performed in quarter": (performed, f"No restore test performed in {r['quarter']}"),
            "B. Restore successful": (str(r["result"]).startswith("Successful") if performed else None,
                                      f"Restore result: {r['result']}"),
        }))
    return pd.DataFrame(rows)


def test_co03(df):
    """CO-03 Batch job failures are logged as incidents and resolved (no timeframe is defined)."""
    rows = []
    for _, r in df.iterrows():
        incident = has_value(r["incident_id"])
        rows.append(result_row(r["run_id"], {
            "A. Incident raised": (incident, f"{r['job_name']} failure with no incident or investigation"),
            "B. Incident resolved (job re-run)": (has_value(r["resolved_date"]) if incident else None,
                                                  "Incident not resolved"),
        }))
    return pd.DataFrame(rows)


# ===========================================================================
# RUN ALL TESTS
# (control, sample file name, population file, test function)
# ===========================================================================
TESTS = [
    ("APD-01", "APD-01", "APD-01_new_users.csv", test_apd01),
    ("APD-02", "APD-02", "APD-02_leavers.csv", test_apd02),
    ("APD-03", "APD-03", "APD-03_uar_reviews.csv", test_apd03),
    ("APD-04", "APD-04", "APD-04_privileged_users.csv", test_apd04),
    ("APD-05", "APD-05", "APD-05_user_listing.csv", test_apd05),
    ("PC-01", "PC-01-02-03", "PC_normal_deployments.csv", test_pc01),
    ("PC-02", "PC-01-02-03", "PC_normal_deployments.csv", test_pc02),
    ("PC-03", "PC-01-02-03", "PC_normal_deployments.csv", test_pc03),
    ("PC-04", "PC-04", "PC_emergency_deployments.csv", test_pc04),
    ("PD-01", "PD-01-02-03", "PD_digital_onboarding.csv", test_pd01),
    ("PD-02", "PD-01-02-03", "PD_digital_onboarding.csv", test_pd02),
    ("PD-03", "PD-01-02-03", "PD_digital_onboarding.csv", test_pd03),
    ("CO-01", "CO-01", "CO-01_backup_failures.csv", test_co01),
    ("CO-02", "CO-02", "CO-02_restore_tests.csv", test_co02),
    ("CO-03", "CO-03", "CO-03_batch_failures.csv", test_co03),
]


def main():
    summary_rows, detected, analytics_rows = [], [], []
    result_sheets = {}

    for control, sample_name, population_file, test in TESTS:
        sample = pd.read_csv(SAMPLE_DIR / f"{sample_name}_sample.csv", dtype=str)
        population = pd.read_csv(POPULATION_DIR / population_file, dtype=str)
        fully_tested = len(sample) == len(population)

        # 1. Sample testing (the formal ToE)
        results = test(sample)
        results.insert(0, "Control", control)
        result_sheets[control] = results
        sample_exceptions = results[results["Result"] == "Exception"]
        for _, e in sample_exceptions.iterrows():
            detected.append({"control_id": control, "record_id": e["Record ID"],
                             "detected_by": "100% testing" if fully_tested else "Sample testing",
                             "comment": e["Comment"]})

        # 2. Full-population analytics (only needed where we sampled)
        population_exceptions = 0
        if not fully_tested:
            full = test(population)
            full_exceptions = full[full["Result"] == "Exception"]
            population_exceptions = len(full_exceptions)
            for _, e in full_exceptions.iterrows():
                in_sample = e["Record ID"] in set(sample_exceptions["Record ID"])
                analytics_rows.append({"Control": control, "Record ID": e["Record ID"],
                                       "Also found in sample?": "Yes" if in_sample else "No",
                                       "Comment": e["Comment"]})
                if not in_sample:
                    detected.append({"control_id": control, "record_id": e["Record ID"],
                                     "detected_by": "Full-population analytics", "comment": e["Comment"]})

        attributes = [c for c in results.columns if c[:2] in ("A.", "B.", "C.", "D.")]
        summary_rows.append({
            "Control": control, "Test procedure": test.__doc__.strip(),
            "Attributes tested": " | ".join(attributes),
            "Population size": len(population), "Items tested": len(sample),
            "Exceptions in items tested": len(sample_exceptions),
            "ToE conclusion (items tested)": "Operating effectively" if sample_exceptions.empty
                                             else "Not operating effectively",
            "Full-population exceptions (analytics)": population_exceptions if not fully_tested else "n/a - 100% tested",
            "Overall conclusion": "Operating effectively"
                                  if sample_exceptions.empty and population_exceptions == 0
                                  else "Not operating effectively - see Exception Log",
        })

    summary = pd.DataFrame(summary_rows)
    analytics = pd.DataFrame(analytics_rows, columns=["Control", "Record ID", "Also found in sample?", "Comment"])
    notes = pd.DataFrame({"Notes": [
        "Each control was tested against its attributes. Any failed attribute = exception.",
        "Simplification: zero tolerance - one exception in the items tested means the control did not operate effectively.",
        "Overall conclusion combines the sample result with full-population analytics: an exception found by either "
        "method means the control did not operate effectively throughout the period.",
        "CO-03: NovaLend has no defined timeframe for resolving batch failures (design gap, see Test of Design), "
        "so only 'incident raised' and 'incident resolved' were tested.",
        "Full-population analytics re-ran the same tests on every record for sampled controls. "
        "Exceptions found only by analytics are reported separately in the Exception Log.",
        "Prepared by: Manjit Mandal  |  Reviewed by: Pending",
    ]})

    write_excel(TESTING_DIR / "ToE_Workpaper.xlsx",
                {"Summary": summary, "Notes": notes, **result_sheets,
                 "Full_Population_Analytics": analytics})
    pd.DataFrame(detected).to_csv(TESTING_DIR / "exceptions_detected.csv", index=False)

    print("Testing complete -> 08_Test_of_Operating_Effectiveness/ToE_Workpaper.xlsx")
    print(summary[["Control", "Items tested", "Exceptions in items tested",
                   "Full-population exceptions (analytics)"]].to_string(index=False))
    print(f"\nTotal exceptions detected: {len(detected)} (see exceptions_detected.csv)")


if __name__ == "__main__":
    main()
