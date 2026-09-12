from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import resolve, reverse


class CourseUrlTests(TestCase):
    def test_dashboard_url_resolves(self):
        self.assertEqual(reverse("courses:dashboard"), "/")
        self.assertEqual(resolve("/").view_name, "courses:dashboard")

    def test_course_list_url_resolves(self):
        self.assertEqual(reverse("courses:course_list"), "/courses/")
        self.assertEqual(resolve("/courses/").view_name, "courses:course_list")

    def test_cbv_classes_used(self):
        from .views import DashboardView, CourseListView, ProfileView
        self.assertEqual(resolve("/").func.view_class, DashboardView)
        self.assertEqual(resolve("/courses/").func.view_class, CourseListView)
        self.assertEqual(resolve("/profile/").func.view_class, ProfileView)


    def test_profile_url_resolves(self):
        self.assertEqual(reverse("courses:profile"), "/profile/")
        self.assertEqual(resolve("/profile/").view_name, "courses:profile")

    def test_profile_requires_login(self):
        response = self.client.get(reverse("courses:profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/signin/", response.url)

    def test_profile_auto_created_and_accessible_when_logged_in(self):
        user = User.objects.create_user(username="testuser", password="password123")
        self.assertTrue(hasattr(user, "profile"))
        self.client.login(username="testuser", password="password123")
        response = self.client.get(reverse("courses:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "testuser")

    def test_course_list_pagination(self):
        user = User.objects.create_user(username="testuser2", password="password123")
        self.client.login(username="testuser2", password="password123")
        from .models import Course
        for i in range(12):
            Course.objects.create(user=user, title=f"Course {i}")

        response = self.client.get(reverse("courses:course_list"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("page_obj", response.context)
        self.assertEqual(len(response.context["page_obj"]), 8)

        response_page2 = self.client.get(reverse("courses:course_list") + "?page=2")
        self.assertEqual(response_page2.status_code, 200)
        self.assertEqual(len(response_page2.context["page_obj"]), 4)

    def test_course_list_search_q_objects_and_filtering(self):
        user = User.objects.create_user(username="testuser3", password="password123")
        self.client.login(username="testuser3", password="password123")
        from .models import Course
        Course.objects.create(user=user, title="Django Web Development", instructor="John Doe", category="Python", status="completed")
        Course.objects.create(user=user, title="React Frontend", instructor="Jane Smith", category="JavaScript", status="in_progress")
        Course.objects.create(user=user, title="Advanced Python Scripting", instructor="John Doe", category="Python", status="not_started")

        # Test Q search query
        res_search = self.client.get(reverse("courses:course_list") + "?q=Django")
        self.assertEqual(res_search.status_code, 200)
        self.assertEqual(len(res_search.context["page_obj"]), 1)
        self.assertEqual(res_search.context["page_obj"][0].title, "Django Web Development")

        # Test status filter
        res_status = self.client.get(reverse("courses:course_list") + "?status=completed")
        self.assertEqual(res_status.status_code, 200)
        self.assertEqual(len(res_status.context["page_obj"]), 1)
        self.assertEqual(res_status.context["page_obj"][0].status, "completed")

        # Test category filter
        res_cat = self.client.get(reverse("courses:course_list") + "?category=Python")
        self.assertEqual(res_cat.status_code, 200)
        self.assertEqual(len(res_cat.context["page_obj"]), 2)

    def test_user_course_isolation(self):
        from .models import Course
        user1 = User.objects.create_user(username="user1", password="password123")
        user2 = User.objects.create_user(username="user2", password="password123")

        course1 = Course.objects.create(user=user1, title="User 1 Course")
        course2 = Course.objects.create(user=user2, title="User 2 Course")

        # Log in as user1
        self.client.login(username="user1", password="password123")
        response = self.client.get(reverse("courses:course_list"))
        self.assertEqual(response.status_code, 200)
        courses_in_view = response.context["page_obj"].object_list
        self.assertIn(course1, courses_in_view)
        self.assertNotIn(course2, courses_in_view)

        # user1 attempting to access user2's course detail should get 404
        detail_response = self.client.get(reverse("courses:course_detail", kwargs={"pk": course2.pk}))
        self.assertEqual(detail_response.status_code, 404)

    def test_performance_timing_middleware_header(self):
        response = self.client.get(reverse("courses:signin"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("X-Performance-Timing-Ms", response.headers)

    def test_course_pre_save_status_auto_sync(self):
        from .models import Course
        course = Course.objects.create(title="Signals Test Course", progress=100, status="not_started")
        # pre_save signal should automatically set status to 'completed'
        self.assertEqual(course.status, "completed")

    def test_task_post_save_and_post_delete_progress_recalculation(self):
        from .models import Course, Task
        course = Course.objects.create(title="Task Signals Course", progress=0, status="not_started")
        task1 = Task.objects.create(course=course, title="Task 1", completed=True)
        task2 = Task.objects.create(course=course, title="Task 2", completed=False)

        # 1 completed out of 2 tasks -> progress should be 50%
        course.refresh_from_db()
        self.assertEqual(course.progress, 50)
        self.assertEqual(course.status, "in_progress")

        # Mark task2 completed
        task2.completed = True
        task2.save()
        course.refresh_from_db()
        self.assertEqual(course.progress, 100)
        self.assertEqual(course.status, "completed")

        # Delete task2 -> 1 completed out of 1 task -> progress should stay 100%
        task2.delete()
        course.refresh_from_db()
        self.assertEqual(course.progress, 100)

    def test_ai_assistant_url_resolves(self):
        self.assertEqual(reverse("courses:ai_assistant"), "/ai-assistant/")
        self.assertEqual(resolve("/ai-assistant/").view_name, "courses:ai_assistant")

    def test_ai_assistant_requires_login(self):
        response = self.client.post(reverse("courses:ai_assistant"), {"prompt": "Hello"})
        # GlobalAuthCheckMiddleware redirects unauthenticated requests
        self.assertEqual(response.status_code, 302)
        self.assertIn("/signin/", response.url)

    def test_ai_assistant_post_success(self):
        user = User.objects.create_user(username="aiuser", password="password123")
        self.client.login(username="aiuser", password="password123")

        response = self.client.post(
            reverse("courses:ai_assistant"),
            data='{"prompt": "Summarize my progress"}',
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data["status"], "success")
        self.assertIn("Learning Progress Summary", json_data["reply"])

    def test_ai_assistant_empty_prompt_validation(self):
        user = User.objects.create_user(username="aiuser2", password="password123")
        self.client.login(username="aiuser2", password="password123")

        response = self.client.post(
            reverse("courses:ai_assistant"),
            data='{"prompt": ""}',
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        json_data = response.json()
        self.assertEqual(json_data["status"], "error")
        self.assertIn("cannot be empty", json_data["message"])







