from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Course, Task


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "instructor",
        "category",
        "progress",
        "status",
        "start_date",
        "end_date",
    )

    list_filter = (
        "status",
        "category",
    )

    search_fields = (
        "title",
        "instructor",
        "category",
    )

    ordering = ("-created_at",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "course",
        "due_date",
        "completed",
    )

    list_filter = (
        "completed",
        "course",
    )

    search_fields = (
        "title",
        "description",
    )

    ordering = ("due_date",)