"""
STEP 5 - Compare audit results with the sealed answer key
=========================================================

Run this ONLY after testing and reporting are finished.

It compares every exception the audit detected with the exceptions that were
deliberately planted in the data (99_Answer_Key_SEALED/answer_key.csv) and
puts each one in a bucket:

    Found by sampling or 100% testing   -> the traditional audit approach found it
    Found only by full-population analytics -> sampling alone would have missed it
    Missed                              -> planted, but the audit did not find it
    False positive                      -> flagged by the audit, but not planted
                                           (needs investigating: test logic or data issue?)

OUTPUT
    10_Reporting/Answer_Key_Reconciliation.xlsx

HOW TO RUN (from the project folder)
    python 10_Reporting/reconcile_answer_key.py
"""

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))
from audit_utils import ANSWER_KEY_DIR, REPORTING_DIR, TESTING_DIR, write_excel


def main():
    planted = pd.read_csv(ANSWER_KEY_DIR / "answer_key.csv")
    detected = pd.read_csv(TESTING_DIR / "exceptions_detected.csv")

    # An outer merge keeps rows that appear in either file, and the
    # 'indicator' column tells us which file(s) each row came from.
    merged = planted.merge(detected, on=["control_id", "record_id"], how="outer", indicator=True)

    def bucket(row):
        if row["_merge"] == "left_only":
            return "Missed"
        if row["_merge"] == "right_only":
            return "False positive"
        if row["detected_by"] == "Full-population analytics":
            return "Found only by full-population analytics"
        return "Found by sampling or 100% testing"

    merged["Outcome"] = merged.apply(bucket, axis=1)
    detail = merged[["exception_id", "control_id", "record_id", "description",
                     "detected_by", "comment", "Outcome"]].rename(columns={
        "exception_id": "Answer key ID", "control_id": "Control", "record_id": "Record ID",
        "description": "Planted exception", "detected_by": "Detected by", "comment": "Audit comment"})
    detail = detail.sort_values(["Control", "Record ID"])

    summary = detail["Outcome"].value_counts().rename_axis("Outcome").reset_index(name="Count")
    by_control = pd.crosstab(detail["Control"], detail["Outcome"]).reset_index()

    write_excel(REPORTING_DIR / "Answer_Key_Reconciliation.xlsx",
                {"Summary": summary, "By_Control": by_control, "Detail": detail})

    print("Answer-key reconciliation -> 10_Reporting/Answer_Key_Reconciliation.xlsx")
    print(f"Planted exceptions: {len(planted)}   Detected by the audit: {len(detected)}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
