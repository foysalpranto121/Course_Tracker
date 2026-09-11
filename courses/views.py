import json
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db.models import Avg, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.safestring import mark_safe
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import (
    CourseForm,
    ProfileUpdateForm,
    SignInForm,
    SignUpForm,
    TaskForm,
    UserUpdateForm,
)
from .models import Course, Task, UserProfile
from .utils import (
    export_courses_to_excel,
    generate_duplicates_excel,
    generate_sample_template,
    import_courses_from_excel,
)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "courses/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        courses = Course.objects.all().order_by("-created_at")[:5]
        total_courses = Course.objects.count()
        active_courses = Course.objects.exclude(status="completed").count()
        completed_courses = Course.objects.filter(status="completed").count()

        avg_progress = Course.objects.aggregate(avg=Avg("progress"))["avg"]
        overall_progress = int(round(avg_progress)) if avg_progress is not None else 0

        context.update(
            {
                "courses": courses,
                "total_courses": total_courses,
                "active_courses": active_courses,
                "completed_courses": completed_courses,
                "overall_progress": overall_progress,
            }
        )
        return context


class ProfileView(LoginRequiredMixin, View):
    template_name = "courses/profile.html"

    def get(self, request, *args, **kwargs):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
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
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, "Your profile has been updated successfully!")
            return redirect("courses:profile")

        messages.error(request, "Please correct the errors in your profile details.")
        total_courses = Course.objects.count()
        completed_courses = Course.objects.filter(status="completed").count()

        context = {
            "u_form": u_form,
            "p_form": p_form,
            "profile": profile,
            "total_courses": total_courses,
            "completed_courses": completed_courses,
        }
        return render(request, self.template_name, context)


class SignUpView(View):
    template_name = "courses/signup.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("courses:dashboard")
        form = SignUpForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("courses:dashboard")
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                f"Welcome to Course Tracker, {user.username}! Your account has been created successfully.",
            )
            return redirect("courses:dashboard")
        return render(request, self.template_name, {"form": form})


class SignInView(View):
    template_name = "courses/signin.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("courses:dashboard")
        next_url = request.GET.get("next", "")
        form = SignInForm()
        return render(request, self.template_name, {"form": form, "next": next_url})

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("courses:dashboard")
        next_url = request.GET.get("next", "") or request.POST.get("next", "")
        form = SignInForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            if next_url:
                return redirect(next_url)
            return redirect("courses:dashboard")

        messages.error(request, "Invalid username or password. Please try again.")
        return render(request, self.template_name, {"form": form, "next": next_url})


class SignOutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, "You have been signed out successfully.")
        return redirect("courses:signin")

    def post(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, "You have been signed out successfully.")
        return redirect("courses:signin")


class CourseListView(LoginRequiredMixin, ListView):
    model = Course
    template_name = "courses/course_list.html"
    context_object_name = "courses"
    paginate_by = 8

    def get_queryset(self):
        queryset = super().get_queryset()

        search_query = self.request.GET.get("q", "").strip()
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query)
                | Q(instructor__icontains=search_query)
                | Q(category__icontains=search_query)
                | Q(description__icontains=search_query)
            )

        status_filter = self.request.GET.get("status", "").strip()
        if status_filter in ["not_started", "in_progress", "completed"]:
            queryset = queryset.filter(status=status_filter)

        category_filter = self.request.GET.get("category", "").strip()
        if category_filter:
            queryset = queryset.filter(category__iexact=category_filter)

        ordering = self.request.GET.get("ordering", "-created_at").strip()
        valid_orderings = {
            "-created_at": "-created_at",
            "created_at": "created_at",
            "title": "title",
            "-title": "-title",
            "-progress": "-progress",
            "progress": "progress",
        }
        sort_field = valid_orderings.get(ordering, "-created_at")
        return queryset.order_by(sort_field)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = context["paginator"]
        page_obj = context["page_obj"]

        page_range = paginator.get_elided_page_range(
            page_obj.number, on_each_side=1, on_ends=1
        )

        search_query = self.request.GET.get("q", "").strip()
        status_filter = self.request.GET.get("status", "").strip()
        category_filter = self.request.GET.get("category", "").strip()
        ordering = self.request.GET.get("ordering", "-created_at").strip()

        available_categories = (
            Course.objects.exclude(category="")
            .values_list("category", flat=True)
            .distinct()
            .order_by("category")
        )

        query_params = self.request.GET.copy()
        if "page" in query_params:
            del query_params["page"]
        encoded_querystring = query_params.urlencode()
        if encoded_querystring:
            encoded_querystring = "&" + encoded_querystring

        is_filtered = bool(
            search_query
            or status_filter
            or category_filter
            or (ordering and ordering != "-created_at")
        )

        context.update(
            {
                "page_range": page_range,
                "search_query": search_query,
                "status_filter": status_filter,
                "category_filter": category_filter,
                "ordering": ordering,
                "available_categories": available_categories,
                "encoded_querystring": encoded_querystring,
                "is_filtered": is_filtered,
                "total_filtered_count": paginator.count,
            }
        )
        return context


class CourseCreateView(LoginRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = "courses/course_form.html"

    def get_success_url(self):
        return reverse("courses:course_detail", kwargs={"pk": self.object.pk})


class CourseDetailView(LoginRequiredMixin, DetailView):
    model = Course
    template_name = "courses/course_detail.html"
    context_object_name = "course"


class CourseUpdateView(LoginRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = "courses/course_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = self.object
        return context

    def get_success_url(self):
        return reverse("courses:course_detail", kwargs={"pk": self.object.pk})


class CourseDeleteView(LoginRequiredMixin, DeleteView):
    model = Course
    template_name = "courses/course_confirm_delete.html"
    context_object_name = "course"
    success_url = reverse_lazy("courses:course_list")


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "courses/task_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.course = get_object_or_404(Course, pk=self.kwargs["course_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial["course"] = self.course
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = self.course
        return context

    def form_valid(self, form):
        task = form.save(commit=False)
        task.course = self.course
        task.save()
        return redirect("courses:course_detail", pk=self.course.pk)


class CourseExportView(LoginRequiredMixin, View):
    """
    Exports courses to Excel (.xlsx) file.
    """

    def get(self, request, *args, **kwargs):
        excel_bytes = export_courses_to_excel()
        response = HttpResponse(
            excel_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="courses_export.xlsx"'
        return response


class CourseExportTemplateView(LoginRequiredMixin, View):
    """
    Downloads sample Excel template for courses import.
    """

    def get(self, request, *args, **kwargs):
        template_bytes = generate_sample_template()
        response = HttpResponse(
            template_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = (
            'attachment; filename="sample_courses_import.xlsx"'
        )
        return response


class CourseImportView(LoginRequiredMixin, View):
    """
    Handles Excel sheet upload for import with duplicate detection, tracking & updating.
    """

    def post(self, request, *args, **kwargs):
        excel_file = request.FILES.get("excel_file")
        duplicate_action = request.POST.get("duplicate_action", "skip")

        if not excel_file:
            messages.error(request, "Please select an Excel or CSV file to import.")
            return redirect("courses:course_list")

        result = import_courses_from_excel(
            excel_file, duplicate_action=duplicate_action
        )

        created = result["created"]
        updated = result["updated"]
        skipped = result["skipped"]
        errors = result["errors"]
        duplicate_rows = result["duplicate_rows"]
        error_msgs = result["error_messages"]

        if duplicate_rows:
            request.session["duplicate_rows"] = duplicate_rows

        summary_parts = []
        if created > 0:
            summary_parts.append(f"<strong>{created}</strong> created")
        if updated > 0:
            summary_parts.append(f"<strong>{updated}</strong> updated")
        if skipped > 0:
            summary_parts.append(f"<strong>{skipped}</strong> skipped (duplicates)")
        if errors > 0:
            summary_parts.append(f"<strong>{errors}</strong> failed/invalid")

        summary_msg = (
            f"Excel Import Completed: {', '.join(summary_parts)}."
            if summary_parts
            else "Import processed."
        )

        if skipped > 0:
            summary_msg += ' <a href="/courses/download-duplicates/" class="alert-link ms-2"><i class="bi bi-download"></i> Download Duplicates Excel Report</a>'
            messages.warning(request, mark_safe(summary_msg))
        else:
            messages.success(request, mark_safe(summary_msg))

        if error_msgs and len(error_msgs) <= 5:
            for err in error_msgs:
                messages.error(request, err)

        return redirect("courses:course_list")


class DownloadDuplicatesView(LoginRequiredMixin, View):
    """
    Generates and downloads Excel sheet of duplicate records tracked during the last import.
    """

    def get(self, request, *args, **kwargs):
        duplicate_rows = request.session.get("duplicate_rows", [])
        if not duplicate_rows:
            messages.info(request, "No duplicate records found to download.")
            return redirect("courses:course_list")

        dup_bytes = generate_duplicates_excel(duplicate_rows)

        response = HttpResponse(
            dup_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = (
            'attachment; filename="duplicate_courses_report.xlsx"'
        )
        return response


class AIAssistantView(LoginRequiredMixin, View):
    """
    AJAX endpoint for the AI Assistant floating chat widget.
    Processes user prompts and returns context-aware AI guidance.
    """

    def post(self, request, *args, **kwargs):
        from .ai_service import generate_assistant_response

        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
            prompt = body.get("prompt", "").strip()
        except Exception:
            prompt = request.POST.get("prompt", "").strip()

        if not prompt:
            return JsonResponse(
                {"status": "error", "message": "Prompt cannot be empty."},
                status=400
            )

        try:
            reply = generate_assistant_response(request.user, prompt)
            return JsonResponse({"status": "success", "reply": reply})
        except Exception as e:
            return JsonResponse(
                {"status": "error", "message": f"An error occurred: {str(e)}"},
                status=500
            )
