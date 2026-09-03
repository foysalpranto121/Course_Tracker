from django.shortcuts import render, redirect, get_object_or_404

from .models import Course, Task
from .forms import CourseForm, TaskForm

def task_create(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk)

    if request.method == "POST":
        form = TaskForm(request.POST)

        if form.is_valid():
            task = form.save(commit=False)
            task.course = course
            task.save()

            return redirect(
                "courses:course_detail",
                pk=course.pk
            )

    else:
        form = TaskForm(initial={"course": course})

    return render(
        request,
        "courses/task_form.html",
        {
            "form": form,
            "course": course,
        }
    )