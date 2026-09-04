from django.contrib import messages
from django.db.models import Avg
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.safestring import mark_safe

from .forms import CourseForm, TaskForm
from .models import Course
from .utils import (
    export_courses_to_excel,
    generate_duplicates_excel,
    generate_sample_template,
    import_courses_from_excel,
)


def dashboard(request):
    courses = Course.objects.all().order_by("-created_at")[:5]
    total_courses = Course.objects.count()
    active_courses = Course.objects.exclude(status="completed").count()
    completed_courses = Course.objects.filter(status="completed").count()

    avg_progress = Course.objects.aggregate(avg=Avg("progress"))["avg"]
    overall_progress = int(round(avg_progress)) if avg_progress is not None else 0

    context = {
        "courses": courses,
        "total_courses": total_courses,
        "active_courses": active_courses,
        "completed_courses": completed_courses,
        "overall_progress": overall_progress,
    }
    return render(request, "courses/dashboard.html", context)


def course_list(request):
    courses = Course.objects.all()
    return render(request, "courses/course_list.html", {"courses": courses})


def course_create(request):
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            return redirect("courses:course_detail", pk=course.pk)
    else:
        form = CourseForm()

    return render(request, "courses/course_form.html", {"form": form})


def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    return render(request, "courses/course_detail.html", {"course": course})


def course_update(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            return redirect("courses:course_detail", pk=course.pk)
    else:
        form = CourseForm(instance=course)

    return render(request, "courses/course_form.html", {"form": form, "course": course})


def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == "POST":
        course.delete()
        return redirect("courses:course_list")

    return render(request, "courses/course_confirm_delete.html", {"course": course})


def task_create(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk)

    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.course = course
            task.save()
            return redirect("courses:course_detail", pk=course.pk)
    else:
        form = TaskForm(initial={"course": course})

    return render(
        request,
        "courses/task_form.html",
        {
            "form": form,
            "course": course,
        },
    )


def course_export(request):
    """
    Exports courses to Excel (.xlsx) file.
    """
    excel_bytes = export_courses_to_excel()
    response = HttpResponse(
        excel_bytes,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="courses_export.xlsx"'
    return response


def course_export_template(request):
    """
    Downloads sample Excel template for courses import.
    """
    template_bytes = generate_sample_template()
    response = HttpResponse(
        template_bytes,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="sample_courses_import.xlsx"'
    return response


def course_import(request):
    """
    Handles Excel sheet upload for import with duplicate detection, tracking & updating.
    """
    if request.method == "POST":
        excel_file = request.FILES.get("excel_file")
        duplicate_action = request.POST.get("duplicate_action", "skip")

        if not excel_file:
            messages.error(request, "Please select an Excel or CSV file to import.")
            return redirect("courses:course_list")

        result = import_courses_from_excel(excel_file, duplicate_action=duplicate_action)

        created = result["created"]
        updated = result["updated"]
        skipped = result["skipped"]
        errors = result["errors"]
        duplicate_rows = result["duplicate_rows"]
        error_msgs = result["error_messages"]

        if duplicate_rows:
            request.session["duplicate_rows"] = duplicate_rows

        # Build user friendly summary notification
        summary_parts = []
        if created > 0:
            summary_parts.append(f"<strong>{created}</strong> created")
        if updated > 0:
            summary_parts.append(f"<strong>{updated}</strong> updated")
        if skipped > 0:
            summary_parts.append(f"<strong>{skipped}</strong> skipped (duplicates)")
        if errors > 0:
            summary_parts.append(f"<strong>{errors}</strong> failed/invalid")

        summary_msg = f"Excel Import Completed: {', '.join(summary_parts)}." if summary_parts else "Import processed."

        if skipped > 0:
            summary_msg += ' <a href="/courses/download-duplicates/" class="alert-link ms-2"><i class="bi bi-download"></i> Download Duplicates Excel Report</a>'
            messages.warning(request, mark_safe(summary_msg))
        else:
            messages.success(request, mark_safe(summary_msg))

        if error_msgs and len(error_msgs) <= 5:
            for err in error_msgs:
                messages.error(request, err)

    return redirect("courses:course_list")


def download_duplicates(request):
    """
    Generates and downloads Excel sheet of duplicate records tracked during the last import.
    """
    duplicate_rows = request.session.get("duplicate_rows", [])
    if not duplicate_rows:
        messages.info(request, "No duplicate records found to download.")
        return redirect("courses:course_list")

    dup_bytes = generate_duplicates_excel(duplicate_rows)

    # Optionally keep or clear session duplicate records
    # request.session.pop("duplicate_rows", None)

    response = HttpResponse(
        dup_bytes,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="duplicate_courses_report.xlsx"'
    return response