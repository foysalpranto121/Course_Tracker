from django.shortcuts import get_object_or_404, redirect, render

from .forms import CourseForm, TaskForm
from .models import Course


def dashboard(request):
    courses = Course.objects.all().order_by("-created_at")[:5]
    total_courses = Course.objects.count()
    active_courses = Course.objects.exclude(status="completed").count()
    completed_courses = Course.objects.filter(status="completed").count()

    if total_courses:
        overall_progress = int(
            round(sum(course.progress for course in Course.objects.all()) / total_courses)
        )
    else:
        overall_progress = 0

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