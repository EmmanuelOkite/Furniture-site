"""
Adds nine living room pieces for the Living Room page.

Prices are placeholders requested by the site owner (from 100k UGX upwards).
Replace them with real prices in the admin before launch.
"""

from decimal import Decimal

from django.db import migrations

LIVING_ROOM_PRODUCTS = [
    {
        "name": "Slatted Black Media Wall",
        "slug": "slatted-black-media-wall",
        "product_type": "TV Units",
        "description": "Floor-to-ceiling black slatted feature wall with a floating low media shelf.",
        "price": Decimal("3400000"),
        "image": "images/living-slatted-media-wall.jpg",
        "image_alt": "Black slatted feature wall with a floating media shelf in a white tiled living room",
    },
    {
        "name": "Teal & Damask Sofa Suite",
        "slug": "teal-damask-sofa-suite",
        "product_type": "Sofa Sets",
        "description": "Teal velvet sofa paired with cream damask armchairs and a low oak coffee table.",
        "price": Decimal("5200000"),
        "image": "images/living-teal-damask-suite.jpg",
        "image_alt": "Teal velvet sofa and cream damask armchairs in a bright open-plan living room",
    },
    {
        "name": "Grey Lounge Sofa & Marble Table",
        "slug": "grey-lounge-sofa-marble-table",
        "product_type": "Sofa Sets",
        "description": "Low grey lounge sofa with a round black marble coffee table on a slim metal frame.",
        "price": Decimal("3600000"),
        "image": "images/living-grey-lounge-marble.jpg",
        "image_alt": "Grey lounge sofa beside a round black marble coffee table on a patterned rug",
    },
    {
        "name": "Oatmeal Sofa & Ottoman Set",
        "slug": "oatmeal-sofa-ottoman-set",
        "product_type": "Sofa Sets",
        "description": "Oatmeal three-seater with a matching ottoman and patterned timber-frame armchairs.",
        "price": Decimal("4300000"),
        "image": "images/living-oatmeal-sofa-ottoman.jpg",
        "image_alt": "Oatmeal sofa and ottoman with patterned wooden armchairs in a sunlit lounge",
    },
    {
        "name": "Blue Velvet Chesterfield Sofa",
        "slug": "blue-velvet-chesterfield-sofa",
        "product_type": "Sofas",
        "description": "Ocean-blue velvet Chesterfield sofa with piped cushions.",
        "price": Decimal("2900000"),
        "image": "images/living-blue-velvet-sofa.jpg",
        "image_alt": "Blue velvet Chesterfield sofa facing a glass coffee table and grey panelled wall",
    },
    {
        "name": "Rattan Armchair & Cream Sofa",
        "slug": "rattan-armchair-cream-sofa",
        "product_type": "Sofa Sets",
        "description": "Cream sofa with a rattan armchair and a glass-topped timber coffee table.",
        "price": Decimal("1950000"),
        "image": "images/living-rattan-lounge-set.jpg",
        "image_alt": "Cream sofa, rattan armchair with patterned cushions and a wooden coffee table",
    },
    {
        "name": "Cream Roll-Arm Sofa",
        "slug": "cream-roll-arm-sofa",
        "product_type": "Sofas",
        "description": "Classic cream roll-arm sofa, shown with a mahogany bookcase and a low TV bench.",
        "price": Decimal("2300000"),
        "image": "images/living-cream-roll-arm-sofa.jpg",
        "image_alt": "Cream roll-arm sofa with a mahogany bookcase, Persian-style rug and TV bench",
    },
    {
        "name": "Wood-Shell Swivel Chair",
        "slug": "wood-shell-swivel-chair",
        "product_type": "Chairs",
        "description": "Curved timber-shell swivel chair with a cream cushion on a four-star base.",
        "price": Decimal("700000"),
        "image": "images/living-wood-swivel-chairs.jpg",
        "image_alt": "Two curved wooden swivel chairs with cream cushions in a double-height living room",
    },
    {
        "name": "Ivory Modular Lounge Suite",
        "slug": "ivory-modular-lounge-suite",
        "product_type": "Sofa Sets",
        "description": "Ivory modular sofas with a matching upholstered ottoman.",
        "price": Decimal("5800000"),
        "image": "images/living-ivory-modular-suite.jpg",
        "image_alt": "Ivory modular sofas and an upholstered ottoman in a white room with tall windows",
    },
]


def forwards(apps, schema_editor):
    Product = apps.get_model("furnitureapp", "Product")
    for data in LIVING_ROOM_PRODUCTS:
        Product.objects.update_or_create(
            slug=data["slug"],
            defaults={**data, "room": "living-room"},
        )


def backwards(apps, schema_editor):
    Product = apps.get_model("furnitureapp", "Product")
    Product.objects.filter(slug__in=[p["slug"] for p in LIVING_ROOM_PRODUCTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("furnitureapp", "0004_collection_products_and_prices"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
