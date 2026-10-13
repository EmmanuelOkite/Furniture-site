"""
Adds nine bedroom pieces for the Bedroom page.

Prices are placeholders requested by the site owner (from 100k UGX upwards).
Replace them with real prices in the admin before launch.
"""

from decimal import Decimal

from django.db import migrations

BEDROOM_PRODUCTS = [
    {
        "name": "Channel-Tufted Bed, White Frame",
        "slug": "channel-tufted-bed-white-frame",
        "product_type": "Beds",
        "description": "Gloss white bed frame with a grey channel-tufted headboard and a matching bedside cabinet.",
        "price": Decimal("2700000"),
        "image": "images/bedroom-channel-tufted-bed.jpg",
        "image_alt": "White bed frame with a grey channel-tufted headboard and white bedside cabinet",
    },
    {
        "name": "Round Pedestal Bedside Table",
        "slug": "round-pedestal-bedside-table",
        "product_type": "Bedside Tables",
        "description": "Slim round bedside table on a tapered pedestal base, in warm taupe.",
        "price": Decimal("350000"),
        "image": "images/bedroom-pedestal-bedside-table.jpg",
        "image_alt": "Round taupe pedestal bedside table beside a cream padded headboard",
    },
    {
        "name": "Upholstered Platform Bed",
        "slug": "upholstered-platform-bed",
        "product_type": "Beds",
        "description": "Soft beige upholstered platform bed with a padded headboard and a cube bedside table.",
        "price": Decimal("3300000"),
        "image": "images/bedroom-upholstered-platform-bed.jpg",
        "image_alt": "Beige upholstered platform bed with layered pillows and a cube bedside table",
    },
    {
        "name": "Two-Tone Velvet Headboard Bed",
        "slug": "two-tone-velvet-headboard-bed",
        "product_type": "Beds",
        "description": "Double bed with a split velvet headboard in sky and navy, with white bedside tables.",
        "price": Decimal("2950000"),
        "image": "images/bedroom-two-tone-headboard-bed.jpg",
        "image_alt": "Bed with a sky-blue and navy velvet headboard between two white bedside tables",
    },
    {
        "name": "Charcoal Panel Headboard Bed",
        "slug": "charcoal-panel-headboard-bed",
        "product_type": "Beds",
        "description": "Wide charcoal panel headboard bed with floating grey bedside shelves.",
        "price": Decimal("3100000"),
        "image": "images/bedroom-charcoal-panel-bed.jpg",
        "image_alt": "Charcoal upholstered panel headboard bed against a slatted timber wall",
    },
    {
        "name": "Linen-Shade Bedside Lamp",
        "slug": "linen-shade-bedside-lamp",
        "product_type": "Lighting",
        "description": "Square linen-shade table lamp on a dark bronze stem and base.",
        "price": Decimal("280000"),
        "image": "images/bedroom-bedside-lamp.jpg",
        "image_alt": "Square linen-shade table lamp glowing on a bedside cabinet",
    },
    {
        "name": "Navy Upholstered Bed",
        "slug": "navy-upholstered-bed",
        "product_type": "Beds",
        "description": "Low navy upholstered bed with a deep cushioned headboard and cream bedside cabinets.",
        "price": Decimal("3450000"),
        "image": "images/bedroom-navy-upholstered-bed.jpg",
        "image_alt": "Navy upholstered bed in a bedroom with damask wallpaper and sliding glass doors",
    },
    {
        "name": "Dressing Table & Bed Set",
        "slug": "dressing-table-bed-set",
        "product_type": "Bedroom Sets",
        "description": "White bed with a channel-tufted headboard, matching dressing table, stool and wardrobe.",
        "price": Decimal("4200000"),
        "image": "images/bedroom-dressing-table-set.jpg",
        "image_alt": "White bed, dressing table with stool and tall white wardrobe in a modern bedroom",
    },
    {
        "name": "Carved Four-Poster Bed",
        "slug": "carved-four-poster-bed",
        "product_type": "Beds",
        "description": "Hand-carved dark wood four-poster bed with a panelled canopy.",
        "price": Decimal("7800000"),
        "image": "images/bedroom-carved-four-poster.jpg",
        "image_alt": "Dark carved wooden four-poster bed with a panelled canopy beside a stone fireplace",
    },
]


def forwards(apps, schema_editor):
    Product = apps.get_model("furnitureapp", "Product")
    for data in BEDROOM_PRODUCTS:
        Product.objects.update_or_create(
            slug=data["slug"],
            defaults={**data, "room": "bedroom"},
        )


def backwards(apps, schema_editor):
    Product = apps.get_model("furnitureapp", "Product")
    Product.objects.filter(slug__in=[p["slug"] for p in BEDROOM_PRODUCTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("furnitureapp", "0005_living_room_products"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
