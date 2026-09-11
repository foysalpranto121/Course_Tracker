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
            Course.objects.create(title=f"Course {i}")

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
        Course.objects.create(title="Django Web Development", instructor="John Doe", category="Python", status="completed")
        Course.objects.create(title="React Frontend", instructor="Jane Smith", category="JavaScript", status="in_progress")
        Course.objects.create(title="Advanced Python Scripting", instructor="John Doe", category="Python", status="not_started")

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




