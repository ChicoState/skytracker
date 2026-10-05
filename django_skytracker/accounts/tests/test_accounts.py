from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class AccountFlowTests(TestCase):
    account_details = {"zip_code": "98101", "birth_date": "2000-05-12"}

    def test_person_can_sign_up_with_an_email_and_log_in(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "email": "sky@example.com",
                "first_name": "Sky",
                "last_name": "Watcher",
                "timezone": "America/Los_Angeles",
                "zip_code": "98101",
                "birth_date": "2000-05-12",
                "email_notifications": "on",
                "password1": "A-strong-password-123",
                "password2": "A-strong-password-123",
            },
        )

        self.assertRedirects(response, reverse("accounts:profile"))
        user = User.objects.get(email="sky@example.com")
        self.assertTrue(user.check_password("A-strong-password-123"))
        self.assertEqual(user.timezone, "America/Los_Angeles")
        self.assertEqual(str(user.birth_date), "2000-05-12")

    def test_email_is_case_insensitively_unique(self):
        User.objects.create_user(
            email="sky@example.com", password="A-strong-password-123", **self.account_details
        )

        response = self.client.post(
            reverse("accounts:signup"),
            {
                "email": "SKY@example.com",
                "timezone": "UTC",
                "zip_code": "98101",
                "birth_date": "2000-05-12",
                "password1": "Another-strong-password-123",
                "password2": "Another-strong-password-123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already uses this email address")

    def test_profile_requires_login(self):
        response = self.client.get(reverse("accounts:profile"))

        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('accounts:profile')}")

    def test_authenticated_person_can_update_profile(self):
        user = User.objects.create_user(
            email="sky@example.com", password="A-strong-password-123", **self.account_details
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("accounts:profile"),
            {
                "email": "sky@example.com",
                "first_name": "Sky",
                "last_name": "Watcher",
                "timezone": "America/Denver",
                "zip_code": "80202",
                "birth_date": "2000-05-12",
                "email_notifications": "on",
            },
        )

        self.assertRedirects(response, reverse("accounts:profile"))
        user.refresh_from_db()
        self.assertEqual(user.timezone, "America/Denver")
        self.assertTrue(user.email_notifications)

    def test_signup_requires_zip_code_and_birth_date(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "email": "sky@example.com",
                "timezone": "UTC",
                "password1": "A-strong-password-123",
                "password2": "A-strong-password-123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required.", count=2)

    def test_person_can_log_in_and_out_with_email(self):
        User.objects.create_user(
            email="sky@example.com", password="A-strong-password-123", **self.account_details
        )

        response = self.client.post(
            reverse("accounts:login"),
            {"username": "sky@example.com", "password": "A-strong-password-123"},
        )
        self.assertRedirects(response, reverse("accounts:profile"))

        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("accounts:login"))

    def test_admin_can_open_the_add_user_page(self):
        admin_user = User.objects.create_superuser(
            email="admin@example.com", password="A-strong-password-123", **self.account_details
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse("admin:accounts_user_add"))

        self.assertEqual(response.status_code, 200)
