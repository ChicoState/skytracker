from django.test import SimpleTestCase
from django.urls import reverse


class FilterPreviewTests(SimpleTestCase):
    def test_preview_page_renders(self):
        response = self.client.get(reverse("filters-preview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Constellation filter preview")
        self.assertContains(response, "Filter constellations")
