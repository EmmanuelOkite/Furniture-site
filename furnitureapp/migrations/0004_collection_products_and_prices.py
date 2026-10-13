"""
Adds the collection pieces and placeholder UGX prices, and marks the four
original sample pieces as featured on the homepage.

Prices are placeholders chosen by the site owner's request ("random prices from
100k UGX"). Replace them with real prices in the admin before launch.
"""

from decimal import Decimal

from django.db import migrations

# slug -> price for the four pieces added in 0002.
EXISTING_PRICES = {
    "velvet-three-seater-sofa": Decimal("2450000"),
    "tufted-leather-sofa": Decimal("3200000"),
    "rounded-boucle-lounge-chair": Decimal("1150000"),
    "tufted-accent-chair": Decimal("650000"),
}

NEW_PRODUCTS = [
    {
        "name": "Pine & White TV Console",
        "slug": "pine-white-tv-console",
        "room": "living-room",
        "product_type": "TV Units",
        "description": "Low TV console with a warm pine top, white frame, open shelves and three drawers.",
        "price": Decimal("1350000"),
        "image": "images/product-pine-tv-console.jpg",
        "image_alt": "White TV console with a pine top, open shelves and three pine drawers",
    },
    {
        "name": "Grey Modular Lounge Sofa",
        "slug": "grey-modular-lounge-sofa",
        "room": "living-room",
        "product_type": "Sofas",
        "description": "Deep, low grey sofa with generous cushions, styled with an oak and steel TV bench.",
        "price": Decimal("4100000"),
        "image": "images/product-grey-modular-sofa.jpg",
        "image_alt": "Long grey modular sofa with coral cushions beside an oak and black steel TV bench",
    },
    {
        "name": "Linen Corner Sectional",
        "slug": "linen-corner-sectional",
        "room": "living-room",
        "product_type": "Sofas",
        "description": "L-shaped sectional in oatmeal linen-look fabric with a chaise end.",
        "price": Decimal("3750000"),
        "image": "images/product-corner-sectional.jpg",
        "image_alt": "Oatmeal L-shaped corner sofa with teal cushions in a bright living room",
    },
    {
        "name": "Velvet Dining Chair",
        "slug": "velvet-dining-chair",
        "room": "dining-room",
        "product_type": "Dining Chairs",
        "description": "Upholstered velvet dining chair on slim black legs. Shown in mustard, emerald, teal, grey and charcoal.",
        "price": Decimal("185000"),
        "image": "images/product-velvet-dining-chairs.jpg",
        "image_alt": "Rows of velvet dining chairs in mustard, emerald, teal, grey and charcoal",
    },
    {
        "name": "Cane-Back Dining Set",
        "slug": "cane-back-dining-set",
        "room": "dining-room",
        "product_type": "Dining Sets",
        "description": "Ivory dining table with oval cane-back chairs and upholstered seats.",
        "price": Decimal("3900000"),
        "image": "images/product-cane-dining-set.jpg",
        "image_alt": "Ivory dining table with white cane-back chairs and white rose centrepieces",
    },
    {
        "name": "Oak Elbow Chair",
        "slug": "oak-elbow-chair",
        "room": "dining-room",
        "product_type": "Dining Chairs",
        "description": "Curved oak elbow chair with a padded charcoal seat.",
        "price": Decimal("320000"),
        "image": "images/product-oak-elbow-chair.jpg",
        "image_alt": "Oak elbow chairs with charcoal seats around white round tables in soft light",
    },
    {
        "name": "Walnut Media Wall Set",
        "slug": "walnut-media-wall-set",
        "room": "living-room",
        "product_type": "TV Units",
        "description": "Walnut-finish TV bench, wall shelf and side cabinet with black and white fronts.",
        "price": Decimal("2800000"),
        "image": "images/product-walnut-media-wall.jpg",
        "image_alt": "Walnut TV bench, floating wall shelf and tall cabinet with black and white doors",
    },
    {
        "name": "Oak Open-Shelf Console",
        "slug": "oak-open-shelf-console",
        "room": "office",
        "product_type": "Bookcases",
        "description": "Low oak bookcase with angled open shelves and black rounded ends.",
        "price": Decimal("850000"),
        "image": "images/product-oak-shelf-console.jpg",
        "image_alt": "Low oak open-shelf console with books and a white desk lamp",
    },
    {
        "name": "Carved Walnut Bedroom Set",
        "slug": "carved-walnut-bedroom-set",
        "room": "bedroom",
        "product_type": "Bedroom Sets",
        "description": "Carved walnut bed with matching bedside tables, wardrobe and TV cabinet.",
        "price": Decimal("6500000"),
        "image": "images/product-carved-bedroom-set.jpg",
        "image_alt": "Carved walnut bed, bedside tables, wardrobe and TV cabinet in a cream bedroom",
    },
    {
        "name": "Patio Lounge & Bistro Set",
        "slug": "patio-lounge-bistro-set",
        "room": "outdoor",
        "product_type": "Outdoor Seating",
        "description": "Long cushioned banquette with round wooden bistro tables and white chairs.",
        "price": Decimal("2600000"),
        "image": "images/product-patio-lounge-set.jpg",
        "image_alt": "Grey cushioned banquette with round wooden tables and white chairs on a terrace",
    },
    {
        "name": "Grey Two-Seater Sofa",
        "slug": "grey-two-seater-sofa",
        "room": "living-room",
        "product_type": "Sofas",
        "description": "Compact two-seater in soft grey fabric with square arms.",
        "price": Decimal("1800000"),
        "image": "images/product-grey-loveseat.jpg",
        "image_alt": "Grey two-seater sofa beside an oak and white coffee table",
    },
    {
        "name": "Round Black Dining Set",
        "slug": "round-black-dining-set",
        "room": "dining-room",
        "product_type": "Dining Sets",
        "description": "Round black pedestal table with four spindle-back chairs.",
        "price": Decimal("2200000"),
        "image": "images/product-round-dining-set.jpg",
        "image_alt": "Round black dining table with black spindle-back chairs",
    },
    {
        "name": "Trestle Desk & Stool",
        "slug": "trestle-desk-stool",
        "room": "office",
        "product_type": "Desks",
        "description": "Timber-top trestle desk paired with a round wooden swivel stool.",
        "price": Decimal("950000"),
        "image": "images/product-trestle-desk.jpg",
        "image_alt": "Timber trestle desk and round wooden stool in a sunlit studio",
    },
]


def forwards(apps, schema_editor):
    Product = apps.get_model("furnitureapp", "Product")
    for slug, price in EXISTING_PRICES.items():
        Product.objects.filter(slug=slug).update(price=price, is_featured=True)
    for data in NEW_PRODUCTS:
        Product.objects.update_or_create(slug=data["slug"], defaults=data)


def backwards(apps, schema_editor):
    Product = apps.get_model("furnitureapp", "Product")
    Product.objects.filter(slug__in=[p["slug"] for p in NEW_PRODUCTS]).delete()
    Product.objects.filter(slug__in=EXISTING_PRICES).update(price=None, is_featured=False)


class Migration(migrations.Migration):

    dependencies = [
        ("furnitureapp", "0003_product_is_featured"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
