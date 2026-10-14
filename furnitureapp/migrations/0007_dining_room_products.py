"""
Adds ten dining room pieces for the Dining Room page.

Prices are placeholders requested by the site owner (from 100k UGX upwards).
Replace them with real prices in the admin before launch.
"""

from decimal import Decimal

from django.db import migrations

DINING_ROOM_PRODUCTS = [
    {
        "name": "Glass-Top Wrought Iron Dining Set",
        "slug": "glass-top-wrought-iron-dining-set",
        "product_type": "Dining Sets",
        "description": "Square glass-top table on a white wrought iron base, with four cushioned iron chairs.",
        "price": Decimal("1650000"),
        "image": "images/dining-glass-iron-set.jpg",
        "image_alt": "White wrought iron dining table with a glass top and four cushioned chairs",
    },
    {
        "name": "Marble & Gold Dining Set",
        "slug": "marble-gold-dining-set",
        "product_type": "Dining Sets",
        "description": "White marble-effect table on gold legs with grey velvet button-back chairs.",
        "price": Decimal("4800000"),
        "image": "images/dining-marble-gold-set.jpg",
        "image_alt": "White marble dining table with grey velvet chairs on gold legs under a crystal chandelier",
    },
    {
        "name": "Refectory Dining Table & Chairs",
        "slug": "refectory-dining-table-chairs",
        "product_type": "Dining Sets",
        "description": "Long dark-wood refectory table with tall ladder-back chairs and green seat pads.",
        "price": Decimal("3700000"),
        "image": "images/dining-refectory-table.jpg",
        "image_alt": "Long dark wooden refectory table with tall chairs on a terracotta tiled floor",
    },
    {
        "name": "Queen Anne Mahogany Dining Set",
        "slug": "queen-anne-mahogany-dining-set",
        "product_type": "Dining Sets",
        "description": "Oval mahogany pedestal table with Queen Anne splat-back chairs.",
        "price": Decimal("4500000"),
        "image": "images/dining-mahogany-queen-anne.jpg",
        "image_alt": "Oval mahogany dining table with Queen Anne chairs in a bay-windowed room",
    },
    {
        "name": "Teak Dining Set",
        "slug": "teak-dining-set",
        "product_type": "Dining Sets",
        "description": "Warm teak dining table with high slatted-back chairs.",
        "price": Decimal("3200000"),
        "image": "images/dining-teak-set.jpg",
        "image_alt": "Teak dining table and high-backed wooden chairs beside a glass balcony wall",
    },
    {
        "name": "Banquet Dining Table, Ladder-Back Chairs",
        "slug": "banquet-dining-table-ladder-back-chairs",
        "product_type": "Dining Sets",
        "description": "Extra-long banquet table seating twelve, with carved ladder-back chairs.",
        "price": Decimal("8200000"),
        "image": "images/dining-banquet-set.jpg",
        "image_alt": "Long banquet table laid with white linen and lined with carved ladder-back chairs",
    },
    {
        "name": "Ivory Panelled Sideboard",
        "slug": "ivory-panelled-sideboard",
        "product_type": "Sideboards",
        "description": "Long ivory sideboard with panelled doors and drawers, on tapered oak legs.",
        "price": Decimal("1900000"),
        "image": "images/dining-ivory-sideboard.jpg",
        "image_alt": "Long ivory panelled sideboard with white vases and a bronze lamp against a charcoal wall",
    },
    {
        "name": "Black Counter-Height Dining Set",
        "slug": "black-counter-height-dining-set",
        "product_type": "Dining Sets",
        "description": "Black counter-height table with six slat-back stools.",
        "price": Decimal("2600000"),
        "image": "images/dining-black-counter-set.jpg",
        "image_alt": "Black counter-height dining table and chairs on a grey checked rug",
    },
    {
        "name": "Espresso Dining Table & Grey Chairs",
        "slug": "espresso-dining-table-grey-chairs",
        "product_type": "Dining Sets",
        "description": "Espresso-stained rectangular table with eight grey upholstered high-back chairs.",
        "price": Decimal("3350000"),
        "image": "images/dining-espresso-table.jpg",
        "image_alt": "Dark espresso dining table with grey upholstered chairs under a brass chandelier",
    },
    {
        "name": "Cream Oval Dining Set",
        "slug": "cream-oval-dining-set",
        "product_type": "Dining Sets",
        "description": "Cream oval table with ladder-back chairs and a slate-grey runner.",
        "price": Decimal("2750000"),
        "image": "images/dining-cream-oval-set.jpg",
        "image_alt": "Cream oval dining table with ladder-back chairs and potted herbs as a centrepiece",
    },
]


def forwards(apps, schema_editor):
    Product = apps.get_model("furnitureapp", "Product")
    for data in DINING_ROOM_PRODUCTS:
        Product.objects.update_or_create(
            slug=data["slug"],
            defaults={**data, "room": "dining-room"},
        )


def backwards(apps, schema_editor):
    Product = apps.get_model("furnitureapp", "Product")
    Product.objects.filter(slug__in=[p["slug"] for p in DINING_ROOM_PRODUCTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("furnitureapp", "0006_bedroom_products"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
