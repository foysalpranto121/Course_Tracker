import io
import datetime
import pandas as pd

# pyrefly: ignore [missing-import]
from django.db.models import Q

from .models import Course

def export_courses_to_excel(queryset=None):
    """
    Exports a queryset of Course objects to an Excel spreadsheet (.xlsx).
    Returns raw bytes of the generated Excel file.
    """
    if queryset is None:
        queryset = Course.objects.all().order_by("-created_at")

    data = []
    for course in queryset:
        data.append({
            "ID": course.id,
            "Title": course.title,
            "Instructor": course.instructor or "",
            "Category": course.category or "",
            "Description": course.description or "",
            "Start Date": course.start_date.strftime("%Y-%m-%d") if course.start_date else "",
            "End Date": course.end_date.strftime("%Y-%m-%d") if course.end_date else "",
            "Progress (%)": course.progress,
            "Status": course.get_status_display(),
            "Created At": course.created_at.strftime("%Y-%m-%d %H:%M") if course.created_at else "",
        })

    df = pd.DataFrame(data)
    
    if df.empty:
        df = pd.DataFrame(columns=[
            "ID", "Title", "Instructor", "Category", "Description", 
            "Start Date", "End Date", "Progress (%)", "Status", "Created At"
        ])

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Courses")
    
    return output.getvalue()


def parse_date_value(val):
    """
    Helper to clean and convert arbitrary date inputs (string, pd.Timestamp, datetime)
    into a python datetime.date or None.
    """
    if pd.isna(val) or val is None or str(val).strip() == "":
        return None

    if isinstance(val, (datetime.date, datetime.datetime)):
        if isinstance(val, datetime.datetime):
            return val.date()
        return val

    val_str = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(val_str, fmt).date()
        except ValueError:
            pass

    try:
        dt = pd.to_datetime(val_str)
        if not pd.isna(dt):
            return dt.date()
    except Exception:
        pass

    return None


def clean_status(val):
    """
    Normalizes status input into one of valid choices: 'not_started', 'in_progress', 'completed'
    """
    if pd.isna(val) or not val:
        return "not_started"

    s_str = str(val).strip().lower().replace(" ", "_").replace("-", "_")
    if s_str in ("not_started", "notstarted", "new", "pending"):
        return "not_started"
    elif s_str in ("in_progress", "inprogress", "ongoing", "active", "started"):
        return "in_progress"
    elif s_str in ("completed", "complete", "finished", "done"):
        return "completed"

    return "not_started"


def clean_progress(val):
    """
    Ensures progress is an integer between 0 and 100.
    """
    if pd.isna(val) or val is None:
        return 0
    try:
        p = int(float(str(val).strip()))
        return max(0, min(100, p))
    except (ValueError, TypeError):
        return 0


def import_courses_from_excel(file_obj, duplicate_action="skip"):
    """
    Imports courses from an uploaded Excel (.xlsx, .xls) or CSV file.
    duplicate_action: 'skip' or 'update'

    Returns a dictionary summarizing:
    - total, created, updated, skipped, errors count
    - duplicate_rows list (for Excel duplicate export)
    - error_messages list
    """
    filename = getattr(file_obj, "name", "").lower()
    
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(file_obj)
        else:
            df = pd.read_excel(file_obj)
    except Exception as e:
        return {
            "total": 0, "created": 0, "updated": 0, "skipped": 0, "errors": 1,
            "duplicate_rows": [],
            "error_messages": [f"Could not read uploaded Excel/CSV file: {str(e)}"]
        }

    if df.empty:
        return {
            "total": 0, "created": 0, "updated": 0, "skipped": 0, "errors": 0,
            "duplicate_rows": [],
            "error_messages": ["Uploaded file contains no data rows."]
        }

    # Normalize column headers mapping
    col_map = {}
    for col in df.columns:
        c_clean = str(col).strip().lower().replace("_", " ")
        if c_clean in ("title", "course title", "course"):
            col_map[col] = "title"
        elif c_clean in ("instructor", "instructor name", "teacher"):
            col_map[col] = "instructor"
        elif c_clean in ("category", "subject"):
            col_map[col] = "category"
        elif c_clean in ("description", "desc", "details"):
            col_map[col] = "description"
        elif c_clean in ("start date", "startdate", "start"):
            col_map[col] = "start_date"
        elif c_clean in ("end date", "enddate", "end"):
            col_map[col] = "end_date"
        elif c_clean in ("progress", "progress (%)", "percentage"):
            col_map[col] = "progress"
        elif c_clean in ("status", "state"):
            col_map[col] = "status"

    df = df.rename(columns=col_map)

    if "title" not in df.columns:
        return {
            "total": 0, "created": 0, "updated": 0, "skipped": 0, "errors": 1,
            "duplicate_rows": [],
            "error_messages": ["Uploaded file is missing required 'Title' column."]
        }

    total_rows = len(df)
    created_count = 0
    updated_count = 0
    skipped_count = 0
    errors_count = 0
    
    duplicate_rows = []
    error_messages = []

    seen_titles_in_file = set()

    for idx, row in df.iterrows():
        row_num = idx + 2  # 1-indexed header + row index
        
        raw_title = str(row.get("title", "")).strip()
        if pd.isna(row.get("title")) or not raw_title or raw_title.lower() == "nan":
            errors_count += 1
            error_messages.append(f"Row {row_num}: Skipped due to missing title.")
            continue

        description = str(row.get("description", "")) if not pd.isna(row.get("description")) else ""
        if description.lower() == "nan":
            description = ""

        instructor = str(row.get("instructor", "")) if not pd.isna(row.get("instructor")) else ""
        if instructor.lower() == "nan":
            instructor = ""

        category = str(row.get("category", "")) if not pd.isna(row.get("category")) else ""
        if category.lower() == "nan":
            category = ""

        start_date = parse_date_value(row.get("start_date"))
        end_date = parse_date_value(row.get("end_date"))
        progress = clean_progress(row.get("progress"))
        status = clean_status(row.get("status"))

        title_lower = raw_title.lower()

        # Check existing database record
        existing_course = Course.objects.filter(title__iexact=raw_title).first()
        is_duplicate_in_file = title_lower in seen_titles_in_file
        is_duplicate = (existing_course is not None) or is_duplicate_in_file

        seen_titles_in_file.add(title_lower)

        if is_duplicate:
            reason = "Duplicate title exists in Database" if existing_course else "Duplicate title repeated in Excel file"
            
            if duplicate_action == "skip":
                skipped_count += 1
                dup_record = {
                    "Excel Row": row_num,
                    "Title": raw_title,
                    "Instructor": instructor,
                    "Category": category,
                    "Description": description,
                    "Start Date": start_date.strftime("%Y-%m-%d") if start_date else "",
                    "End Date": end_date.strftime("%Y-%m-%d") if end_date else "",
                    "Progress (%)": progress,
                    "Status": status,
                    "Duplicate Reason": reason,
                }
                duplicate_rows.append(dup_record)
                continue
            elif duplicate_action == "update":
                if existing_course:
                    existing_course.description = description
                    existing_course.instructor = instructor
                    existing_course.category = category
                    if start_date:
                        existing_course.start_date = start_date
                    if end_date:
                        existing_course.end_date = end_date
                    existing_course.progress = progress
                    existing_course.status = status
                    existing_course.save()
                    updated_count += 1
                    continue
                else:
                    # Duplicate within file only, update/create latest row
                    existing_course = Course.objects.create(
                        title=raw_title,
                        description=description,
                        instructor=instructor,
                        category=category,
                        start_date=start_date,
                        end_date=end_date,
                        progress=progress,
                        status=status,
                    )
                    updated_count += 1
                    continue

        # New non-duplicate course creation
        try:
            Course.objects.create(
                title=raw_title,
                description=description,
                instructor=instructor,
                category=category,
                start_date=start_date,
                end_date=end_date,
                progress=progress,
                status=status,
            )
            created_count += 1
        except Exception as e:
            errors_count += 1
            error_messages.append(f"Row {row_num} ('{raw_title}'): Failed to save - {str(e)}")

    return {
        "total": total_rows,
        "created": created_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "errors": errors_count,
        "duplicate_rows": duplicate_rows,
        "error_messages": error_messages,
    }


def generate_duplicates_excel(duplicate_rows):
    """
    Generates an Excel spreadsheet (.xlsx) containing skipped duplicate records with reason.
    Returns raw bytes.
    """
    df = pd.DataFrame(duplicate_rows)
    if df.empty:
        df = pd.DataFrame(columns=[
            "Excel Row", "Title", "Instructor", "Category", "Description",
            "Start Date", "End Date", "Progress (%)", "Status", "Duplicate Reason"
        ])

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Duplicate Records")
    
    return output.getvalue()


def generate_sample_template():
    """
    Generates a pre-filled sample template Excel file (.xlsx) for users to populate.
    Returns raw bytes.
    """
    sample_data = [
        {
            "Title": "Full-Stack Python & Django Masterclass",
            "Instructor": "Dr. Angela Yu",
            "Category": "Web Development",
            "Description": "Learn full-stack development with Python 3, Django 5, PostgreSQL, and REST APIs.",
            "Start Date": "2026-09-01",
            "End Date": "2026-11-30",
            "Progress (%)": 25,
            "Status": "in_progress",
        },
        {
            "Title": "Data Analysis & Machine Learning with Pandas",
            "Instructor": "Jose Portilla",
            "Category": "Data Science",
            "Description": "Comprehensive guide to pandas, numpy, scikit-learn, and data visualization.",
            "Start Date": "2026-10-01",
            "End Date": "2026-12-15",
            "Progress (%)": 0,
            "Status": "not_started",
        },
        {
            "Title": "UI/UX Design Essentials in Figma",
            "Instructor": "Daniel Walter Scott",
            "Category": "Design",
            "Description": "Master modern UI design principles, responsive web layouts, and interactive prototypes.",
            "Start Date": "2026-08-01",
            "End Date": "2026-08-30",
            "Progress (%)": 100,
            "Status": "completed",
        },
    ]

    df = pd.DataFrame(sample_data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Courses Template")

    return output.getvalue()
