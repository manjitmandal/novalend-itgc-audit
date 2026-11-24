"""
audit_utils.py - small helpers shared by every NovaLend audit script.

Keeping these in one place means every script uses the SAME audit period,
the SAME folder paths and the SAME definition of a "business day".
"""

from datetime import date, timedelta
from pathlib import Path

from openpyxl.styles import Alignment, Font, PatternFill

# ---------------------------------------------------------------------------
# Audit settings
# ---------------------------------------------------------------------------
AUDIT_START = date(2025, 4, 1)    # NovaLend financial year FY 2025-26
AUDIT_END = date(2026, 3, 31)

# ---------------------------------------------------------------------------
# Folder paths (everything is relative to the project folder)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "03_Data"
VALIDATION_DIR = PROJECT_ROOT / "06_Population_Validation"
POPULATION_DIR = VALIDATION_DIR / "populations"
SAMPLING_DIR = PROJECT_ROOT / "07_Sampling"
SAMPLE_DIR = SAMPLING_DIR / "samples"
TESTING_DIR = PROJECT_ROOT / "08_Test_of_Operating_Effectiveness"
REPORTING_DIR = PROJECT_ROOT / "10_Reporting"
ANSWER_KEY_DIR = PROJECT_ROOT / "99_Answer_Key_SEALED"


# ---------------------------------------------------------------------------
# Business-day helpers
# Simplification: a business day is Monday-Friday. Public holidays are ignored.
# ---------------------------------------------------------------------------
def is_business_day(d):
    """True if the date is Monday (0) to Friday (4)."""
    return d.weekday() < 5


def add_business_days(start, n):
    """Return the date that is n business days after start."""
    d = start
    added = 0
    while added < n:
        d = d + timedelta(days=1)
        if is_business_day(d):
            added += 1
    return d


def business_days_between(start, end):
    """
    Count business days from start to end, not counting the start date.
    Examples: Friday -> Monday = 1, Friday -> Tuesday = 2, same day = 0.
    A negative number means end is BEFORE start.
    """
    if end < start:
        return -business_days_between(end, start)
    count = 0
    d = start
    while d < end:
        d = d + timedelta(days=1)
        if is_business_day(d):
            count += 1
    return count


def to_date(value):
    """Convert a 'YYYY-MM-DD' text value to a date. Blank values become None."""
    if value is None or str(value).strip() in ("", "nan", "NaT", "None"):
        return None
    return date.fromisoformat(str(value)[:10])


# ---------------------------------------------------------------------------
# Excel formatting helper
# ---------------------------------------------------------------------------
HEADER_FILL = PatternFill("solid", start_color="1F3864")
HEADER_FONT = Font(name="Arial", bold=True, color="FFFFFF")
BODY_FONT = Font(name="Arial", size=10)


def format_sheet(ws, max_width=60):
    """Bold dark header row, Arial font, sensible column widths, frozen header."""
    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.font = BODY_FONT
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    for column in ws.columns:
        longest = max(len(str(c.value)) if c.value is not None else 0 for c in column)
        ws.column_dimensions[column[0].column_letter].width = min(max(longest + 2, 10), max_width)
    ws.freeze_panes = "A2"


def write_excel(path, sheets):
    """
    Write several DataFrames to one Excel workbook and format every sheet.
    sheets = {"Sheet name": dataframe, ...}
    """
    import pandas as pd

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
            format_sheet(writer.sheets[name[:31]])
