"""
run_all.py - run the whole NovaLend audit pipeline in order.

    Step 1  03_Data/generate_data.py                         create the synthetic data
    Step 2  06_Population_Validation/validate_populations.py  check data + build populations
    Step 3  07_Sampling/select_samples.py                     select samples
    Step 4  08_Test_of_Operating_Effectiveness/test_controls.py  test controls
    Step 5  10_Reporting/reconcile_answer_key.py              compare with the answer key

HOW TO RUN (from the project folder)
    python run_all.py              run steps 1-5
    python run_all.py --no-key     run steps 1-4 only (audit "blind", answer key unopened)
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

STEPS = [
    "03_Data/generate_data.py",
    "06_Population_Validation/validate_populations.py",
    "07_Sampling/select_samples.py",
    "08_Test_of_Operating_Effectiveness/test_controls.py",
    "10_Reporting/reconcile_answer_key.py",
]

if "--no-key" in sys.argv:
    STEPS = STEPS[:-1]

for number, script in enumerate(STEPS, start=1):
    print(f"\n=== Step {number}: {script} ===")
    subprocess.run([sys.executable, str(PROJECT_ROOT / script)], check=True)

print("\nAll steps finished.")
