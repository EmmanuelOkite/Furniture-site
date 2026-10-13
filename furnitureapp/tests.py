from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Product
from .views import search_products

# Tests run with DEBUG=False, where the manifest storage needs `collectstatic` first.
# Plain storage lets templates render without a build step.
PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=PLAIN_STATIC_STORAGE)
class SearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Start from a known set, independent of the sample-data migration.
        Product.objects.all().delete()
        cls.sofa = Product.objects.create(
            name="Velvet Sofa", slug="velvet-sofa", room=Product.Room.LIVING_ROOM,
            product_type="Sofas", description="Forest-green velvet.",
        )
        cls.bed = Product.objects.create(
            name="Oak Bed Frame", slug="oak-bed-frame", room=Product.Room.BEDROOM,
            product_type="Beds", description="Solid oak.",
        )
        cls.hidden = Product.objects.create(
            name="Hidden Sofa", slug="hidden-sofa", room=Product.Room.LIVING_ROOM,
            product_type="Sofas", is_active=False,
        )

    def test_matches_name_case_insensitively(self):
        self.assertQuerySetEqual(search_products("VELVET"), [self.sofa])

    def test_matches_description(self):
        self.assertQuerySetEqual(search_products("green"), [self.sofa])

    def test_matches_room_label(self):
        self.assertQuerySetEqual(search_products("bedroom"), [self.bed])

    def test_every_word_must_match(self):
        self.assertQuerySetEqual(search_products("green sofa"), [self.sofa])
        self.assertQuerySetEqual(search_products("green bed"), [])

    def test_inactive_products_are_excluded(self):
        self.assertNotIn(self.hidden, search_products("sofa"))

    def test_page_shows_results(self):
        response = self.client.get(reverse("search"), {"q": "oak"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Oak Bed Frame")
        self.assertContains(response, "1 piece found")

    def test_page_shows_empty_state_when_nothing_matches(self):
        response = self.client.get(reverse("search"), {"q": "trampoline"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nothing matched")
        self.assertNotContains(response, "product-card__name")

    def test_blank_query_shows_prompt_only(self):
        response = self.client.get(reverse("search"), {"q": "   "})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "What are you looking for?")
        self.assertNotContains(response, "Nothing matched")

    def test_price_is_shown_in_ugx(self):
        self.sofa.price = 2450000
        self.sofa.save()
        response = self.client.get(reverse("search"), {"q": "velvet"})
        self.assertContains(response, "UGX 2,450,000")

    def test_query_is_escaped(self):
        response = self.client.get(reverse("search"), {"q": "<script>alert(1)</script>"})
        self.assertNotContains(response, "<script>alert(1)</script>")


@override_settings(STORAGES=PLAIN_STATIC_STORAGE)
class CollectionAndHomeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Product.objects.all().delete()
        cls.bed = Product.objects.create(
            name="Oak Bed Frame", slug="oak-bed-frame", room=Product.Room.BEDROOM,
            product_type="Beds", description="Solid oak.", price=1500000, is_featured=True,
        )
        cls.table = Product.objects.create(
            name="Round Table", slug="round-table", room=Product.Room.DINING_ROOM,
            product_type="Tables", price=900000,
        )
        cls.hidden = Product.objects.create(
            name="Hidden Chair", slug="hidden-chair", room=Product.Room.BEDROOM,
            product_type="Chairs", is_active=False,
        )

    def test_collection_lists_all_active_products(self):
        response = self.client.get(reverse("collection"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Oak Bed Frame")
        self.assertContains(response, "Round Table")
        self.assertNotContains(response, "Hidden Chair")
        self.assertContains(response, "Solid oak.")  # details are shown

    def test_collection_filters_by_room(self):
        response = self.client.get(reverse("collection"), {"room": "bedroom"})
        self.assertContains(response, "Oak Bed Frame")
        self.assertNotContains(response, "Round Table")

    def test_unknown_room_shows_everything(self):
        response = self.client.get(reverse("collection"), {"room": "garage"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Round Table")

    def test_empty_room_shows_message(self):
        response = self.client.get(reverse("collection"), {"room": "outdoor"})
        self.assertContains(response, "Nothing here yet")

    def test_home_shows_only_featured_products(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Oak Bed Frame")
        self.assertContains(response, "UGX 1,500,000")
        self.assertNotContains(response, "Round Table")
