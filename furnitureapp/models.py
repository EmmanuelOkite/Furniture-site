from django.contrib.staticfiles import finders
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from .rooms import ROOM_PAGES


class Product(models.Model):
    """A piece of furniture shown on the site."""

    class Room(models.TextChoices):
        LIVING_ROOM = "living-room", "Living Room"
        BEDROOM = "bedroom", "Bedroom"
        DINING_ROOM = "dining-room", "Dining Room"
        OFFICE = "office", "Office Furniture"
        OUTDOOR = "outdoor", "Outdoor Furniture"

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    room = models.CharField(max_length=20, choices=Room.choices)
    product_type = models.CharField(
        max_length=60,
        help_text="Short type label, e.g. Sofas, Accent Chairs, Dining Tables.",
    )
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Leave empty to show “Price coming soon”.",
    )
    # Temporary: a path inside /static (e.g. "images/product-velvet-sofa.jpg").
    # Replace with an ImageField once media storage for uploads is chosen,
    # because Render's disk is wiped on every deploy.
    image = models.CharField(
        max_length=200,
        blank=True,
        help_text="Static image path, e.g. images/product-velvet-sofa.jpg",
    )
    image_alt = models.CharField(max_length=200, blank=True)
    is_sample = models.BooleanField(
        default=False,
        help_text="Marks placeholder pieces that are not real inventory.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive products are hidden from the site and search.",
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Featured products appear in “Pieces You’ll Love” on the homepage.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @classmethod
    def room_url(cls, room):
        """Page that lists a room: its own page if it has one, otherwise the collection filter."""
        if room in ROOM_PAGES:
            return reverse(ROOM_PAGES[room]["url_name"])
        return f"{reverse('collection')}?room={room}"

    def get_absolute_url(self):
        # Products have no detail page yet, so link to the card on its room's page.
        return f"{self.room_url(self.room)}#{self.slug}"

    def clean(self):
        # A wrong path would break the page in production (manifest static storage),
        # so check it when the product is saved through the admin.
        if self.image and not finders.find(self.image):
            raise ValidationError({"image": f"No static file found at “{self.image}”."})
