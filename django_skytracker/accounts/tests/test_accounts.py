from django.test import TestCase
from django.urls import reverse

from accounts.models import Location, User
from accounts.models import SavedEvent


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

    def test_profile_offers_a_link_back_to_home(self):
        user = User.objects.create_user(
            email="sky@example.com", password="A-strong-password-123", **self.account_details
        )
        self.client.force_login(user)

        response = self.client.get(reverse("accounts:profile"))

        self.assertContains(response, '<a href="/">Home</a>')

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

    def test_authenticated_person_can_save_and_view_an_event(self):
        user = User.objects.create_user(
            email="sky@example.com", password="A-strong-password-123", **self.account_details
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("accounts:saved_events"),
            {"event_id": "meteor-shower-2026", "label": "Watch this shower"},
        )

        self.assertRedirects(response, reverse("accounts:saved_events"))
        saved_event = SavedEvent.objects.get(owner=user)
        self.assertEqual(saved_event.event_id, "meteor-shower-2026")
        self.assertContains(self.client.get(reverse("accounts:saved_events")), "Watch this shower")

    def test_saved_events_are_isolated_between_users(self):
        owner = User.objects.create_user(
            email="owner@example.com", password="A-strong-password-123", **self.account_details
        )
        other_user = User.objects.create_user(
            email="other@example.com", password="A-strong-password-123", **self.account_details
        )
        SavedEvent.objects.create(owner=owner, event_id="private-event", label="Private")
        self.client.force_login(other_user)

        response = self.client.get(reverse("accounts:saved_events"))

        self.assertNotContains(response, "Private")
        self.assertEqual(response.context["saved_events"].count(), 0)

    def test_saved_events_require_login(self):
        response = self.client.get(reverse("accounts:saved_events"))

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('accounts:saved_events')}",
        )

    def test_person_can_create_and_manage_a_location(self):
        user = User.objects.create_user(
            email="sky@example.com", password="A-strong-password-123", **self.account_details
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("accounts:location_create"),
            {
                "label": "Home",
                "latitude": "39.7285",
                "longitude": "-121.8375",
                "elevation_meters": "70",
                "timezone": "America/Los_Angeles",
            },
        )

        self.assertRedirects(response, reverse("accounts:locations"))
        location = Location.objects.get(owner=user)
        self.assertEqual(location.label, "Home")
        self.assertEqual(str(location.latitude), "39.7285")

    def test_location_management_is_owner_scoped(self):
        owner = User.objects.create_user(
            email="owner@example.com", password="A-strong-password-123", **self.account_details
        )
        other_user = User.objects.create_user(
            email="other@example.com", password="A-strong-password-123", **self.account_details
        )
        location = Location.objects.create(
            owner=owner,
            label="Private home",
            latitude="39.7285",
            longitude="-121.8375",
            timezone="America/Los_Angeles",
        )
        self.client.force_login(other_user)

        response = self.client.get(reverse("accounts:location_edit", args=[location.pk]))

        self.assertEqual(response.status_code, 404)

    def test_saved_event_button_is_idempotent(self):
        user = User.objects.create_user(
            email="sky@example.com", password="A-strong-password-123", **self.account_details
        )
        self.client.force_login(user)
        payload = {"event_id": "moonrise:2026-10-19:39.7285:-121.8375", "label": "Moonrise"}

        self.client.post(reverse("accounts:saved_events"), payload)
        self.client.post(reverse("accounts:saved_events"), payload)

        self.assertEqual(SavedEvent.objects.filter(owner=user).count(), 1)
