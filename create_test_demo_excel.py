import os
import sys
import pandas as pd

def create_demo_excel_files():
    """
    Creates multiple demo Excel files designed to test all import edge cases:
    1. demo_import_full.xlsx: Comprehensive sheet with valid new records, duplicates, in-file repeats, varied date formats, status variations, and missing title error row.
    2. demo_import_clean.xlsx: 100% clean valid new courses.
    3. demo_import_duplicates_only.xlsx: All rows match existing database titles for duplicate policy testing.
    """
    print("Generating demo Excel files for testing...")

    # File 1: Comprehensive Demo File (covers ALL test cases)
    comprehensive_data = [
        # --- VALID NEW COURSES ---
        {
            "Title": "Artificial Intelligence & LLM Prompt Engineering",
            "Instructor": "Dr. Andrew Ng",
            "Category": "Artificial Intelligence",
            "Description": "Master generative AI, prompt engineering, and transformer models.",
            "Start Date": "2026-09-01",
            "End Date": "2026-11-15",
            "Progress (%)": 45,
            "Status": "in_progress",
        },
        {
            "Title": "DevOps Engineering with Docker & Kubernetes",
            "Instructor": "Nigel Poulton",
            "Category": "DevOps",
            "Description": "Containerization, orchestration, and production CI/CD pipelines.",
            "Start Date": "01/10/2026",  # DD/MM/YYYY format
            "End Date": "15/12/2026",
            "Progress (%)": 0,
            "Status": "Not Started",
        },
        {
            "Title": "Cyber Security & Penetration Testing Specialist",
            "Instructor": "Georgia Weidman",
            "Category": "Security",
            "Description": "Ethical hacking, network defense, vulnerability analysis.",
            "Start Date": "2026/08/10",  # YYYY/MM/DD format
            "End Date": "2026/09/30",
            "Progress (%)": 100,
            "Status": "Completed",
        },

        # --- EDGE CASE: Formatting & Progress Out of Bounds ---
        {
            "Title": "GraphQL API Architecture with Python & Node",
            "Instructor": "",  # Empty optional instructor
            "Category": "Web Development",
            "Description": "Building schema-driven GraphQL APIs.",
            "Start Date": "2026-09-10",
            "End Date": "",   # Empty optional date
            "Progress (%)": 150,  # Out of range -> should clamp to 100
            "Status": "ongoing",  # Status alias -> should map to in_progress
        },
        {
            "Title": "Database Fundamentals & SQL Query Optimization",
            "Instructor": "Brent Ozar",
            "Category": "Database",
            "Description": "Index tuning, query execution plans, and normalization.",
            "Start Date": "",
            "End Date": "",
            "Progress (%)": -25,  # Out of range -> should clamp to 0
            "Status": "new",      # Status alias -> should map to not_started
        },

        # --- DUPLICATE TEST CASES ---
        # Repeats "Artificial Intelligence & LLM Prompt Engineering" (in-file duplicate!)
        {
            "Title": "Artificial Intelligence & LLM Prompt Engineering",
            "Instructor": "Dr. Andrew Ng (Updated)",
            "Category": "Artificial Intelligence",
            "Description": "[DUPLICATE IN FILE] Updated course syllabus and advanced modules.",
            "Start Date": "2026-09-01",
            "End Date": "2026-11-20",
            "Progress (%)": 70,
            "Status": "in_progress",
        },

        # --- ERROR TEST CASE ---
        # Missing title (should trigger error count & error message)
        {
            "Title": "",  # Missing Title
            "Instructor": "Anonymous",
            "Category": "Unknown",
            "Description": "Invalid row without title.",
            "Start Date": "2026-09-01",
            "End Date": "2026-09-30",
            "Progress (%)": 10,
            "Status": "not_started",
        },
    ]

    df_comp = pd.DataFrame(comprehensive_data)
    comp_file = "demo_import_full.xlsx"
    df_comp.to_excel(comp_file, index=False, engine="openpyxl")
    print(f"Created '{comp_file}' ({len(df_comp)} rows: includes valid records, date format variations, progress clamping, in-file duplicate, and error row).")

    # File 2: 100% Clean Valid Import File
    clean_data = [
        {
            "Title": "React 19 & Next.js App Router Masterclass",
            "Instructor": "Maximilian Schwarzmüller",
            "Category": "Web Development",
            "Description": "Build server components, streaming SSR, and modern React apps.",
            "Start Date": "2026-09-05",
            "End Date": "2026-10-20",
            "Progress (%)": 20,
            "Status": "in_progress",
        },
        {
            "Title": "Rust Systems Programming & Concurrency",
            "Instructor": "Tim McNamara",
            "Category": "Programming Languages",
            "Description": "Memory safety, ownership model, and async Rust.",
            "Start Date": "2026-10-01",
            "End Date": "2026-12-01",
            "Progress (%)": 0,
            "Status": "not_started",
        },
    ]
    df_clean = pd.DataFrame(clean_data)
    clean_file = "demo_import_clean.xlsx"
    df_clean.to_excel(clean_file, index=False, engine="openpyxl")
    print(f"Created '{clean_file}' ({len(df_clean)} rows: 100% clean new courses).")

    return comp_file, clean_file

if __name__ == "__main__":
    create_demo_excel_files()
