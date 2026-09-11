from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.safestring import mark_safe

from .forms import (
    CourseForm,
    ProfileUpdateForm,
    SignInForm,
    SignUpForm,
    TaskForm,
    UserUpdateForm,
)
from .models import Course, UserProfile
from .utils import (
    export_courses_to_excel,
    generate_duplicates_excel,
    generate_sample_template,
    import_courses_from_excel,
)


@login_required
def profile_view(request):
    """
    Handles user profile viewing and updating, including profile picture uploads.
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, "Your profile has been updated successfully!")
            return redirect("courses:profile")
        else:
            messages.error(request, "Please correct the errors in your profile details.")
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=profile)

    total_courses = Course.objects.count()
    completed_courses = Course.objects.filter(status="completed").count()

    context = {
        "u_form": u_form,
        "p_form": p_form,
        "profile": profile,
        "total_courses": total_courses,
        "completed_courses": completed_courses,
    }
    return render(request, "courses/profile.html", context)



def signup_view(request):
    """
    Handles user registration/signup.
    """
    if request.user.is_authenticated:
        return redirect("courses:dashboard")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                f"Welcome to Course Tracker, {user.username}! Your account has been created successfully.",
            )
            return redirect("courses:dashboard")
    else:
        form = SignUpForm()

    return render(request, "courses/signup.html", {"form": form})


def signin_view(request):
    """
    Handles user authentication/signin.
    """
    if request.user.is_authenticated:
        return redirect("courses:dashboard")

    next_url = request.GET.get("next", "") or request.POST.get("next", "")

    if request.method == "POST":
        form = SignInForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            if next_url:
                return redirect(next_url)
            return redirect("courses:dashboard")
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = SignInForm()

    return render(request, "courses/signin.html", {"form": form, "next": next_url})


def signout_view(request):
    """
    Handles user logout.
    """
    logout(request)
    messages.info(request, "You have been signed out successfully.")
    return redirect("courses:signin")


@login_required
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


@login_required
def course_list(request):
    courses = Course.objects.all()
    return render(request, "courses/course_list.html", {"courses": courses})


@login_required
def course_create(request):
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            return redirect("courses:course_detail", pk=course.pk)
    else:
        form = CourseForm()

    return render(request, "courses/course_form.html", {"form": form})


@login_required
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    return render(request, "courses/course_detail.html", {"course": course})


@login_required
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


@login_required
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == "POST":
        course.delete()
        return redirect("courses:course_list")

    return render(request, "courses/course_confirm_delete.html", {"course": course})


@login_required
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


@login_required
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


@login_required
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


@login_required
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


@login_required
def download_duplicates(request):
    """
    Generates and downloads Excel sheet of duplicate records tracked during the last import.
    """
    duplicate_rows = request.session.get("duplicate_rows", [])
    if not duplicate_rows:
        messages.info(request, "No duplicate records found to download.")
        return redirect("courses:course_list")

    dup_bytes = generate_duplicates_excel(duplicate_rows)

    response = HttpResponse(
        dup_bytes,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="duplicate_courses_report.xlsx"'
    return response