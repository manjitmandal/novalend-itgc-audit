"""
STEP 3 - Select audit samples
=============================

WHY AUDITORS SAMPLE
    Inspecting evidence (opening each ticket, checking each approval) takes
    time, so auditors usually test a SAMPLE of items from the population and
    use the result to conclude on the whole population.

HOW THIS SCRIPT SAMPLES
    - Sample size depends on how often the control runs and how big the
      population is (see SAMPLE SIZE RULES below).
    - Items are picked at RANDOM, using a fixed RANDOM SEED. The same seed
      always picks the same items, so a reviewer can re-run this script and
      get exactly the same sample. That is called reproducibility.

    IMPORTANT: there is no single universal audit sampling formula. Each audit
    firm has its own methodology. The table below is a SIMPLIFIED, illustrative
    learning approach.

OUTPUT
    07_Sampling/samples/<control>_sample.csv   one file per control
    07_Sampling/Sampling_Workpaper.xlsx        sampling documentation

HOW TO RUN (from the project folder)
    python 07_Sampling/select_samples.py
"""

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))
from audit_utils import POPULATION_DIR, SAMPLE_DIR, SAMPLING_DIR, write_excel

RANDOM_SEED = 20260515   # fixed seed = reproducible sample (documented in the workpaper)

# (control, population file, how often the control operates)
CONTROLS = [
    ("APD-01", "APD-01_new_users.csv", "Event-driven"),
    ("APD-02", "APD-02_leavers.csv", "Event-driven"),
    ("APD-03", "APD-03_uar_reviews.csv", "Quarterly"),
    ("APD-04", "APD-04_privileged_users.csv", "Point-in-time listing"),
    ("APD-05", "APD-05_user_listing.csv", "Point-in-time listing"),
    ("PC-01/02/03", "PC_normal_deployments.csv", "Event-driven"),
    ("PC-04", "PC_emergency_deployments.csv", "Event-driven"),
    ("PD-01/02/03", "PD_digital_onboarding.csv", "One-off project"),
    ("CO-01", "CO-01_backup_failures.csv", "Event-driven"),
    ("CO-02", "CO-02_restore_tests.csv", "Quarterly"),
    ("CO-03", "CO-03_batch_failures.csv", "Event-driven"),
]

# ---------------------------------------------------------------------------
# SAMPLE SIZE RULES (simplified learning table)
# ---------------------------------------------------------------------------
SAMPLE_SIZE_TABLE = pd.DataFrame([
    {"Control frequency / population": "Population of 4 items or fewer", "Sample size": "Test all items"},
    {"Control frequency / population": "Quarterly control", "Sample size": "2 (all 4 when population is 4)"},
    {"Control frequency / population": "Point-in-time listing or one-off project", "Sample size": "Test 100% (inspect the whole listing / project file)"},
    {"Control frequency / population": "Event-driven, up to 52 items a year", "Sample size": "10 (or all, if fewer than 10)"},
    {"Control frequency / population": "Event-driven, 53 to 250 items", "Sample size": "25"},
    {"Control frequency / population": "Event-driven, more than 250 items", "Sample size": "40"},
])


def choose_sample_size(frequency, population_size):
    """Apply the simplified sample size table above."""
    if population_size <= 4:
        return population_size
    if frequency == "Quarterly":
        return 2
    if frequency in ("Point-in-time listing", "One-off project"):
        return population_size
    if population_size <= 52:
        return min(10, population_size)
    if population_size <= 250:
        return 25
    return 40


def safe_name(control):
    """'PC-01/02/03' cannot be a file name, so turn it into 'PC-01-02-03'."""
    return control.replace("/", "-")


def main():
    SAMPLE_DIR.mkdir(exist_ok=True)
    summary_rows = []
    sample_sheets = {}

    for control, population_file, frequency in CONTROLS:
        population = pd.read_csv(POPULATION_DIR / population_file, dtype=str)
        size = choose_sample_size(frequency, len(population))

        if size == len(population):
            sample = population.copy()                                   # test everything
            method = "Whole population tested"
        else:
            sample = population.sample(n=size, random_state=RANDOM_SEED)  # random selection
            sample = sample.sort_index()
            method = f"Random selection, pandas .sample(random_state={RANDOM_SEED})"

        sample.insert(0, "sample_no", range(1, len(sample) + 1))
        sample.to_csv(SAMPLE_DIR / f"{safe_name(control)}_sample.csv", index=False)
        sample_sheets[safe_name(control)] = sample

        summary_rows.append({
            "Control": control, "Population file": population_file,
            "Control frequency": frequency, "Population size": len(population),
            "Sample size": size, "Selection method": method,
            "Sample file": f"samples/{safe_name(control)}_sample.csv",
        })

    summary = pd.DataFrame(summary_rows)
    method_notes = pd.DataFrame({"Sampling methodology": [
        "Objective: select items to test whether each control operated effectively throughout FY 2025-26.",
        "Populations come from 06_Population_Validation, where completeness and accuracy were checked first.",
        f"Random seed: {RANDOM_SEED}. Re-running select_samples.py with this seed reproduces exactly the same sample.",
        "Sample sizes follow a SIMPLIFIED learning table (sheet Sample_Size_Table). Real audit firms use their own methodology.",
        "Controls with small populations, listings and the one-off project were tested in full (100%).",
        "Prepared by: Manjit Mandal  |  Reviewed by: Pending",
    ]})

    write_excel(SAMPLING_DIR / "Sampling_Workpaper.xlsx",
                {"Summary": summary, "Methodology": method_notes,
                 "Sample_Size_Table": SAMPLE_SIZE_TABLE, **sample_sheets})

    print("Samples selected -> 07_Sampling/samples/ and Sampling_Workpaper.xlsx")
    print(summary[["Control", "Population size", "Sample size"]].to_string(index=False))


if __name__ == "__main__":
    main()
