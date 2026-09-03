from django.shortcuts import render, redirect, get_object_or_404

from .models import Course, Task
from .forms import CourseForm, TaskForm


def dashboard(request):
    courses = Course.objects.all()

    total_courses = courses.count()
    completed_courses = courses.filter(status="completed").count()
    active_courses = courses.filter(status="in_progress").count()

    if total_courses:
        overall_progress = sum(
            course.progress for course in courses
        ) // total_courses
    else:
        overall_progress = 0

    context = {
        "courses": courses[:5],
        "total_courses": total_courses,
        "completed_courses": completed_courses,
        "active_courses": active_courses,
        "overall_progress": overall_progress,
    }

    return render(request, "courses/dashboard.html", context)


def course_list(request):
    courses = Course.objects.all()

    return render(
        request,
        "courses/course_list.html",
        {"courses": courses}
    )


def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)

    return render(
        request,
        "courses/course_detail.html",
        {"course": course}
    )


def course_create(request):
    if request.method == "POST":
        form = CourseForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("courses:course_list")

    else:
        form = CourseForm()

    return render(
        request,
        "courses/course_form.html",
        {"form": form}
    )


def course_update(request, pk):
    course = get_object_or_404(Course, pk=pk)

    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)

        if form.is_valid():
            form.save()
            return redirect(
                "courses:course_detail",
                pk=course.pk
            )

    else:
        form = CourseForm(instance=course)

    return render(
        request,
        "courses/course_form.html",
        {
            "form": form,
            "course": course,
        }
    )


def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)

    if request.method == "POST":
        course.delete()
        return redirect("courses:course_list")

    return render(
        request,
        "courses/course_confirm_delete.html",
        {"course": course}
    )


def task_create(request):
    if request.method == "POST":
        form = TaskForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("courses:course_list")

    else:
        form = TaskForm()

    return render(
        request,
        "courses/task_form.html",
        {"form": form}
    )