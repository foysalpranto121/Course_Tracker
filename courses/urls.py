from django.urls import path
from . import views

app_name = "courses"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    path("courses/", views.course_list, name="course_list"),
    path("courses/create/", views.course_create, name="course_create"),
    path("courses/<int:pk>/", views.course_detail, name="course_detail"),
    path("courses/<int:pk>/edit/", views.course_update, name="course_update"),
    path("courses/<int:pk>/delete/", views.course_delete, name="course_delete"),

    path("tasks/create/", views.task_create, name="task_create"),
]