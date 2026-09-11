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

    def test_auth_urls_resolve(self):
        self.assertEqual(reverse("courses:signin"), "/signin/")
        self.assertEqual(reverse("courses:signup"), "/signup/")
        self.assertEqual(reverse("courses:signout"), "/signout/")

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("courses:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/signin/", response.url)

    def test_signin_page_accessible(self):
        response = self.client.get(reverse("courses:signin"))
        self.assertEqual(response.status_code, 200)

    def test_signup_page_accessible(self):
        response = self.client.get(reverse("courses:signup"))
        self.assertEqual(response.status_code, 200)

