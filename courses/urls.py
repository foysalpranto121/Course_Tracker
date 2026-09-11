from django.urls import path
from . import views

app_name = "courses"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),

    # Auth & Profile CBV routes
    path("signup/", views.SignUpView.as_view(), name="signup"),
    path("signin/", views.SignInView.as_view(), name="signin"),
    path("signout/", views.SignOutView.as_view(), name="signout"),
    path("profile/", views.ProfileView.as_view(), name="profile"),

    # Course CBV routes
    path("courses/", views.CourseListView.as_view(), name="course_list"),
    path("courses/create/", views.CourseCreateView.as_view(), name="course_create"),
    path("courses/export/", views.CourseExportView.as_view(), name="course_export"),
    path("courses/export-template/", views.CourseExportTemplateView.as_view(), name="course_export_template"),
    path("courses/import/", views.CourseImportView.as_view(), name="course_import"),
    path("courses/download-duplicates/", views.DownloadDuplicatesView.as_view(), name="download_duplicates"),
    path("courses/<int:pk>/", views.CourseDetailView.as_view(), name="course_detail"),
    path("courses/<int:pk>/edit/", views.CourseUpdateView.as_view(), name="course_update"),
    path("courses/<int:pk>/delete/", views.CourseDeleteView.as_view(), name="course_delete"),

    # Task CBV route
    path(
        "courses/<int:course_pk>/tasks/create/",
        views.TaskCreateView.as_view(),
        name="task_create"
    ),
]

