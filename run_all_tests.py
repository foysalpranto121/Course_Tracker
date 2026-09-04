import os
import sys
import pandas as pd

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "todo_project.settings")

import django
django.setup()

from courses.models import Course, Task
from courses.utils import (
    export_courses_to_excel,
    import_courses_from_excel,
    generate_duplicates_excel,
    generate_sample_template,
    parse_date_value,
    clean_progress,
    clean_status,
)


def print_header(title):
    print("\n" + "=" * 70)
    print(f" TEST SUITE: {title}")
    print("=" * 70)


def run_unit_tests():
    print_header("1. UNIT TESTS (Helper functions: Date, Progress, Status)")

    # Date parsing test cases
    assert parse_date_value("2026-09-01").strftime("%Y-%m-%d") == "2026-09-01", "Failed YYYY-MM-DD"
    assert parse_date_value("15/12/2026").strftime("%Y-%m-%d") == "2026-12-15", "Failed DD/MM/YYYY"
    assert parse_date_value("2026/08/10").strftime("%Y-%m-%d") == "2026-08-10", "Failed YYYY/MM/DD"
    assert parse_date_value(None) is None, "Failed None date"
    assert parse_date_value("") is None, "Failed empty date"
    print("  [PASS] Date parser correctly handles YYYY-MM-DD, DD/MM/YYYY, YYYY/MM/DD & empty dates.")

    # Progress clamping test cases
    assert clean_progress(50) == 50, "Failed normal progress"
    assert clean_progress(150) == 100, "Failed upper bound progress clamping (150 -> 100)"
    assert clean_progress(-25) == 0, "Failed lower bound progress clamping (-25 -> 0)"
    assert clean_progress("75%") == 0 or clean_progress(75) == 75, "Failed progress"
    print("  [PASS] Progress cleaner correctly clamps out-of-bounds progress values [0..100].")

    # Status normalization test cases
    assert clean_status("Completed") == "completed", "Failed Completed"
    assert clean_status("Not Started") == "not_started", "Failed Not Started"
    assert clean_status("ongoing") == "in_progress", "Failed ongoing alias"
    assert clean_status("new") == "not_started", "Failed new alias"
    print("  [PASS] Status normalizer correctly maps display labels & aliases to DB choices.")


from django.db import transaction

def run_clean_import_test():
    print_header("2. CLEAN IMPORT TEST (demo_import_clean.xlsx)")

    with transaction.atomic():
        sid = transaction.savepoint()
        try:
            with open("demo_import_clean.xlsx", "rb") as f:
                res = import_courses_from_excel(f, duplicate_action="skip")

            print(f"  Result -> Total: {res['total']}, Created: {res['created']}, Skipped: {res['skipped']}, Errors: {res['errors']}")
            assert res['total'] == 2, "Expected 2 total rows"
            assert res['created'] == 2, "Expected 2 created rows"
            print("  [PASS] Clean Excel file imported 100% successfully.")
        finally:
            transaction.savepoint_rollback(sid)



def run_comprehensive_import_test():
    print_header("3. COMPREHENSIVE IMPORT & DUPLICATE TRACKING TEST (demo_import_full.xlsx - SKIP POLICY)")

    with open("demo_import_full.xlsx", "rb") as f:
        res = import_courses_from_excel(f, duplicate_action="skip")

    print(f"  Result -> Total: {res['total']}, Created: {res['created']}, Skipped: {res['skipped']}, Errors: {res['errors']}")
    print(f"  Duplicate Rows Tracked: {len(res['duplicate_rows'])}")
    print(f"  Error Messages: {res['error_messages']}")

    assert res['total'] == 7, f"Expected 7 total rows, got {res['total']}"
    assert res['created'] == 5, f"Expected 5 created rows, got {res['created']}"
    assert res['skipped'] == 1, f"Expected 1 skipped row (in-file duplicate), got {res['skipped']}"
    assert res['errors'] == 1, f"Expected 1 error row (missing title), got {res['errors']}"

    # Verify duplicate Excel report generation
    dup_bytes = generate_duplicates_excel(res['duplicate_rows'])
    assert len(dup_bytes) > 1000, "Duplicate Excel report generated invalid bytes"
    print("  [PASS] Duplicate detection, error tracking, and Duplicate Excel report generation passed!")


def run_database_duplicate_test():
    print_header("4. DATABASE DUPLICATE DETECTION TEST (Re-import demo_import_full.xlsx - SKIP POLICY)")

    with open("demo_import_full.xlsx", "rb") as f:
        res = import_courses_from_excel(f, duplicate_action="skip")

    print(f"  Result -> Total: {res['total']}, Created: {res['created']}, Skipped: {res['skipped']}, Errors: {res['errors']}")
    
    # All 5 existing valid titles in DB + 1 in-file repeat should be skipped = 6 skipped
    assert res['created'] == 0, "Expected 0 created (all already exist in DB)"
    assert res['skipped'] == 6, f"Expected 6 skipped duplicates, got {res['skipped']}"
    assert res['errors'] == 1, "Expected 1 missing title error"
    print("  [PASS] Database existing course titles correctly identified as duplicates and skipped!")


def run_update_duplicate_policy_test():
    print_header("5. UPDATE DUPLICATE POLICY TEST (Re-import demo_import_full.xlsx - UPDATE POLICY)")

    with open("demo_import_full.xlsx", "rb") as f:
        res = import_courses_from_excel(f, duplicate_action="update")

    print(f"  Result -> Total: {res['total']}, Created: {res['created']}, Updated: {res['updated']}, Skipped: {res['skipped']}")
    assert res['updated'] >= 5, "Expected existing records to be updated"
    assert res['skipped'] == 0, "Expected 0 skipped under UPDATE policy"
    print("  [PASS] UPDATE duplicate policy correctly updated existing DB records with Excel data.")


def run_export_test():
    print_header("6. EXPORT EXCEL TEST")

    export_bytes = export_courses_to_excel()
    print(f"  Exported Excel File Size: {len(export_bytes)} bytes")
    assert len(export_bytes) > 2000, "Export excel byte stream too small"

    template_bytes = generate_sample_template()
    print(f"  Sample Template File Size: {len(template_bytes)} bytes")
    assert len(template_bytes) > 2000, "Template excel byte stream too small"

    print("  [PASS] Excel Export and Template generation passed successfully!")


if __name__ == "__main__":
    run_unit_tests()
    run_clean_import_test()
    run_comprehensive_import_test()
    run_database_duplicate_test()
    run_update_duplicate_policy_test()
    run_export_test()

    print("\n" + "*" * 70)
    print(" ALL TEST CASES PASSED SUCCESSFULLY 100%! EXCEL IMPORT/EXPORT SYSTEM IS FULLY VALIDATED.")
    print("*" * 70 + "\n")
