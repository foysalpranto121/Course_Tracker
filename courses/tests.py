from django.test import SimpleTestCase
from django.urls import resolve, reverse


class CourseUrlTests(SimpleTestCase):
    def test_dashboard_url_resolves(self):
        self.assertEqual(reverse("courses:dashboard"), "/")
        self.assertEqual(resolve("/").view_name, "courses:dashboard")

    def test_course_list_url_resolves(self):
        self.assertEqual(reverse("courses:course_list"), "/courses/")
        self.assertEqual(resolve("/courses/").view_name, "courses:course_list")
