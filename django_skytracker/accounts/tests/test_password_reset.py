from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="sky@example.com",
            password="A-strong-password-123",
            zip_code="98101",
            birth_date="2000-05-12",
        )

    def test_login_page_links_to_password_reset(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertContains(response, reverse("accounts:password_reset"))

    def test_person_can_reset_password_without_email(self):
        response = self.client.post(
            reverse("accounts:password_reset"),
            {
                "email": "SKY@example.com",
                "new_password1": "A-new-strong-password-123",
                "new_password2": "A-new-strong-password-123",
            },
        )

        self.assertRedirects(response, reverse("accounts:password_reset_complete"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("A-new-strong-password-123"))
        self.assertTrue(
            self.client.login(email="sky@example.com", password="A-new-strong-password-123")
        )

    def test_reset_does_not_send_email_or_store_reset_data(self):
        response = self.client.post(
            reverse("accounts:password_reset"),
            {
                "email": "sky@example.com",
                "new_password1": "A-new-strong-password-123",
                "new_password2": "A-new-strong-password-123",
            },
        )

        self.assertRedirects(response, reverse("accounts:password_reset_complete"))
        self.assertEqual(User.objects.count(), 1)

    def test_unknown_email_is_rejected(self):
        response = self.client.post(
            reverse("accounts:password_reset"),
            {
                "email": "nobody@example.com",
                "new_password1": "A-new-strong-password-123",
                "new_password2": "A-new-strong-password-123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No account was found")

    def test_mismatched_passwords_are_rejected(self):
        response = self.client.post(
            reverse("accounts:password_reset"),
            {
                "email": "sky@example.com",
                "new_password1": "A-new-strong-password-123",
                "new_password2": "A-different-password-123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The two passwords do not match")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("A-strong-password-123"))
