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


class LandingPageView(TemplateView):
    template_name = "courses/landing.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("courses:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        total_courses_count = Course.objects.count()
        total_users_count = User.objects.count()
        total_tasks_count = Task.objects.count()

        context.update(
            {
                "total_courses_count": total_courses_count,
                "total_users_count": total_users_count,
                "total_tasks_count": total_tasks_count,
            }
        )
        return context


class GuestSignInView(View):
    def get(self, request, *args, **kwargs):
        return self.login_guest(request)

    def post(self, request, *args, **kwargs):
        return self.login_guest(request)

    def login_guest(self, request):
        guest_username = "guest_demo"
        user, created = User.objects.get_or_create(
            username=guest_username,
            defaults={
                "first_name": "Guest",
                "last_name": "Explorer",
                "email": "guest@example.com",
            },
        )
        if created:
            user.set_unusable_password()
            user.save()

        # Ensure user profile exists
        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "institution": "Open Learning Lab",
                "occupation": "Guest Explorer",
                "learning_goal": "Explore AI Course Tracker features",
                "bio": "I am exploring the live demo environment of AI Course Tracker.",
            },
        )

        # Seed initial sample data if guest user has no courses
        if not Course.objects.filter(user=user).exists():
            from datetime import timedelta
            from django.utils import timezone
            today = timezone.now().date()

            c1 = Course.objects.create(
                user=user,
                title="Full-Stack Web Development with Django 5",
                instructor="Dr. Angela Yu",
                instructor_email="angela@example.com",
                category="Web Development",
                description="Master modern web app development, PostgreSQL database design, REST APIs, and Render deployment.",
                start_date=today - timedelta(days=15),
                end_date=today + timedelta(days=45),
                progress=65,
                status="in_progress",
            )
            Task.objects.create(
                course=c1,
                title="Complete PostgreSQL Database Schema Design",
                description="Define models, primary keys, foreign keys, and indexes.",
                due_date=today - timedelta(days=2),
                completed=True,
            )
            Task.objects.create(
                course=c1,
                title="Build Interactive REST API Endpoints",
                description="Implement serializers and viewsets for course models.",
                due_date=today + timedelta(days=3),
                completed=False,
            )
            Task.objects.create(
                course=c1,
                title="Deploy Web Service to Render",
                description="Configure Gunicorn, WhiteNoise, build.sh, and render.yaml.",
                due_date=today + timedelta(days=7),
                completed=False,
            )

            c2 = Course.objects.create(
                user=user,
                title="Data Science & Machine Learning Essentials",
                instructor="Jose Portilla",
                instructor_email="jose@example.com",
                category="Data Science",
                description="Learn Python data analysis, pandas dataframes, numpy computations, and Excel import/export processing.",
                start_date=today - timedelta(days=30),
                end_date=today + timedelta(days=10),
                progress=90,
                status="in_progress",
            )
            Task.objects.create(
                course=c2,
                title="Clean and Filter Dataset using Pandas",
                description="Handle missing values, duplicate rows, and date format parsing.",
                due_date=today - timedelta(days=5),
                completed=True,
            )
            Task.objects.create(
                course=c2,
                title="Export Formatted Analytics Report to Excel",
                description="Generate .xlsx output with openpyxl engine.",
                due_date=today + timedelta(days=1),
                completed=False,
            )

            c3 = Course.objects.create(
                user=user,
                title="UI/UX Responsive Design in Bootstrap 5",
                instructor="Daniel Walter Scott",
                instructor_email="daniel@example.com",
                category="Design",
                description="Design modern glassmorphism web interfaces, dark themes, animated progress cards, and mobile layouts.",
                start_date=today - timedelta(days=60),
                end_date=today - timedelta(days=5),
                progress=100,
                status="completed",
            )
            Task.objects.create(
                course=c3,
                title="Build Dark Glassmorphic Dashboard Navbar",
                description="Style translucent headers with subtle border glows.",
                due_date=today - timedelta(days=10),
                completed=True,
            )

        login(request, user)
        messages.success(
            request,
            "⚡ Welcome to Guest Demo Mode! You are logged in as a Guest User with pre-loaded sample courses and AI Assistant context.",
        )
        return redirect("courses:dashboard")


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "courses/dashboard.html"


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_courses = Course.objects.filter(user=self.request.user)
        courses = user_courses.order_by("-created_at")[:5]
        total_courses = user_courses.count()
        active_courses = user_courses.exclude(status="completed").count()
        completed_courses = user_courses.filter(status="completed").count()

        avg_progress = user_courses.aggregate(avg=Avg("progress"))["avg"]
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

        total_courses = Course.objects.filter(user=request.user).count()
        completed_courses = Course.objects.filter(user=request.user, status="completed").count()

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
        total_courses = Course.objects.filter(user=request.user).count()
        completed_courses = Course.objects.filter(user=request.user, status="completed").count()

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
                f"Welcome to AI Course Tracker, {user.username}! Your account has been created successfully.",
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
        queryset = Course.objects.filter(user=self.request.user)

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
            Course.objects.filter(user=self.request.user)
            .exclude(category="")
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

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("courses:course_detail", kwargs={"pk": self.object.pk})


class CourseDetailView(LoginRequiredMixin, DetailView):
    model = Course
    template_name = "courses/course_detail.html"
    context_object_name = "course"

    def get_queryset(self):
        return Course.objects.filter(user=self.request.user)


class CourseUpdateView(LoginRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = "courses/course_form.html"

    def get_queryset(self):
        return Course.objects.filter(user=self.request.user)

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

    def get_queryset(self):
        return Course.objects.filter(user=self.request.user)


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "courses/task_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.course = get_object_or_404(Course, pk=self.kwargs["course_pk"], user=request.user)
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
        excel_bytes = export_courses_to_excel(user=request.user)
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
            excel_file, duplicate_action=duplicate_action, user=request.user
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


class SendInstructorEmailView(LoginRequiredMixin, View):
    """
    Manually triggers sending course completion notification email to the instructor.
    """

    def post(self, request, pk, *args, **kwargs):
        from django.conf import settings
        from django.core.mail import send_mail
        from django.utils import timezone

        course = get_object_or_404(Course, pk=pk, user=request.user)

        if not course.instructor_email:
            messages.error(
                request,
                "This course does not have an instructor email set. Please edit the course to add an instructor email address."
            )
            return redirect("courses:course_detail", pk=course.pk)

        student_name = request.user.get_full_name() or request.user.username
        student_email = request.user.email or "Not provided"
        subject = f"🎓 Course Completion Notice: {course.title}"
        message = (
            f"Dear Instructor,\n\n"
            f"This is an official automated completion notice from the AI Course Tracker platform.\n\n"
            f"Student Details:\n"
            f"- Name: {student_name}\n"
            f"- Student Email: {student_email}\n\n"
            f"Course Summary:\n"
            f"- Title: {course.title}\n"
            f"- Category: {course.category or 'General'}\n"
            f"- Progress: 100% Completed\n"
            f"- Completion Date: {timezone.now().strftime('%B %d, %Y at %H:%M UTC')}\n\n"
            f"Thank you for guiding the student!\n\n"
            f"Best regards,\n"
            f"AI Course Tracker System"
        )

        from .signals import send_email_async

        send_email_async(
            subject=subject,
            message=message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[course.instructor_email],
        )
        messages.success(
            request,
            f"Completion notification email queued & sending to instructor ({course.instructor_email})!"
        )

        return redirect("courses:course_detail", pk=course.pk)

