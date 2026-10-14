from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.test import TestCase
from django.urls import reverse

from .models import Department, Student, Faculty


class RegistrationWorkflowTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            department_id=9001,
            name="Recovery Test Department",
            description="Temporary test data",
        )
        self.password = "LearningPass123"

    def student_payload(self, **overrides):
        data = {
            "account_id": "91001",
            "name": "Test Student",
            "email": "student.test@example.com",
            "department": str(self.department.pk),
            "password": self.password,
            "confirm_password": self.password,
        }
        data.update(overrides)
        return data

    def faculty_payload(self, **overrides):
        data = {
            "account_id": "92001",
            "name": "Test Faculty",
            "email": "faculty.test@example.com",
            "department": str(self.department.pk),
            "password": self.password,
            "confirm_password": self.password,
        }
        data.update(overrides)
        return data

    def test_student_registration_hashes_password(self):
        response = self.client.post(
            reverse("student_register"),
            self.student_payload(),
        )

        self.assertRedirects(response, reverse("std_login"))
        student = Student.objects.get(student_id=91001)
        self.assertTrue(check_password(self.password, student.password))
        self.assertNotEqual(student.password, self.password)
        self.assertEqual(student.role, "Student")

    def test_faculty_registration_hashes_password(self):
        response = self.client.post(
            reverse("faculty_register"),
            self.faculty_payload(),
        )

        self.assertRedirects(response, reverse("std_login"))
        faculty = Faculty.objects.get(faculty_id=92001)
        self.assertTrue(check_password(self.password, faculty.password))
        self.assertNotEqual(faculty.password, self.password)
        self.assertEqual(faculty.role, "Faculty")

    def test_student_duplicate_id_is_rejected(self):
        Student.objects.create(
            student_id=91001,
            name="Existing Student",
            email="existing.student@example.com",
            password="unused",
            department=self.department,
        )

        response = self.client.post(
            reverse("student_register"),
            self.student_payload(email="another.student@example.com"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already registered")
        self.assertEqual(Student.objects.filter(student_id=91001).count(), 1)

    def test_student_duplicate_email_is_rejected_case_insensitively(self):
        Student.objects.create(
            student_id=91002,
            name="Existing Student",
            email="student.test@example.com",
            password="unused",
            department=self.department,
        )

        response = self.client.post(
            reverse("student_register"),
            self.student_payload(account_id="91003"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already registered")
        self.assertFalse(Student.objects.filter(student_id=91003).exists())

    def test_password_mismatch_is_rejected(self):
        response = self.client.post(
            reverse("student_register"),
            self.student_payload(confirm_password="DifferentPass123"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "passwords do not match")
        self.assertFalse(Student.objects.filter(student_id=91001).exists())

    def test_invalid_department_is_rejected(self):
        response = self.client.post(
            reverse("student_register"),
            self.student_payload(department="999999"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Student.objects.filter(student_id=91001).exists())

    def test_registered_student_can_log_in(self):
        self.client.post(
            reverse("student_register"),
            self.student_payload(),
        )

        response = self.client.post(
            reverse("std_login"),
            {"id": "91001", "password": self.password},
        )

        self.assertRedirects(response, reverse("myCourses"))
        self.assertEqual(
            self.client.session.get("student_id"),
            91001,
        )

    def test_registered_faculty_can_log_in(self):
        self.client.post(
            reverse("faculty_register"),
            self.faculty_payload(),
        )

        response = self.client.post(
            reverse("std_login"),
            {"id": "92001", "password": self.password},
        )

        self.assertRedirects(response, reverse("facultyCourses"))
        self.assertEqual(
            self.client.session.get("faculty_id"),
            92001,
        )

    def test_dashboard_redirects_anonymous_user(self):
        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_staff_user_can_open_dashboard(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="recovery_test_admin",
            password="TemporaryTestPassword123!",
            is_staff=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin_dashboard.html")
