"""
Adds ten outdoor pieces for the Outdoor Furniture page.

Prices are placeholders requested by the site owner (from 100k UGX upwards).
Replace them with real prices in the admin before launch.
"""

from decimal import Decimal

from django.db import migrations

OUTDOOR_PRODUCTS = [
    {
        "name": "Rattan Egg Chair Lounge Set",
        "slug": "rattan-egg-chair-lounge-set",
        "product_type": "Lounge Sets",
        "description": "Woven rattan sofa, two egg lounge chairs and a round coffee table with cream cushions.",
        "price": Decimal("4200000"),
        "image": "images/outdoor-rattan-egg-lounge.jpg",
        "image_alt": "Woven rattan sofa, egg chairs and round coffee table with cream cushions on a patio",
    },
    {
        "name": "Folding Canvas Camp Chair",
        "slug": "folding-canvas-camp-chair",
        "product_type": "Outdoor Chairs",
        "description": "Lightweight folding chair with a sand canvas seat and wooden armrests.",
        "price": Decimal("180000"),
        "image": "images/outdoor-folding-camp-chair.jpg",
        "image_alt": "Sand canvas folding camp chairs around a fire pit on a lawn",
    },
    {
        "name": "Rustic Pine Garden Dining Set",
        "slug": "rustic-pine-garden-dining-set",
        "product_type": "Outdoor Dining",
        "description": "Long pine trestle table with cross-back chairs for garden dining.",
        "price": Decimal("3800000"),
        "image": "images/outdoor-pine-garden-dining.jpg",
        "image_alt": "Long rustic pine garden table with cross-back wooden chairs under a thatched umbrella",
    },
    {
        "name": "Sage Slatted Bistro Chair",
        "slug": "sage-slatted-bistro-chair",
        "product_type": "Outdoor Chairs",
        "description": "Sage-green powder-coated metal armchair with a slatted seat and back.",
        "price": Decimal("320000"),
        "image": "images/outdoor-sage-bistro-chair.jpg",
        "image_alt": "Sage-green slatted metal bistro armchairs in dappled garden shade",
    },
    {
        "name": "Teak Cube Side Table",
        "slug": "teak-cube-side-table",
        "product_type": "Outdoor Tables",
        "description": "Open-sided teak cube table that doubles as a low stool.",
        "price": Decimal("240000"),
        "image": "images/outdoor-teak-cube-table.jpg",
        "image_alt": "Teak cube side tables on a gravel terrace beside folding garden chairs",
    },
    {
        "name": "Black Aluminium Lounge Set",
        "slug": "black-aluminium-lounge-set",
        "product_type": "Lounge Sets",
        "description": "Black aluminium-frame sofa and armchair with striped cushions and a low coffee table.",
        "price": Decimal("3600000"),
        "image": "images/outdoor-black-aluminium-lounge.jpg",
        "image_alt": "Black aluminium sofa and armchair with striped cushions on a covered timber deck",
    },
    {
        "name": "Striped Outdoor Bean Bag",
        "slug": "striped-outdoor-bean-bag",
        "product_type": "Loungers",
        "description": "Weather-resistant striped bean bag lounger, shown in mustard and green.",
        "price": Decimal("220000"),
        "image": "images/outdoor-striped-bean-bag.jpg",
        "image_alt": "Mustard and green striped bean bag loungers on a sandy beach",
    },
    {
        "name": "Garden Gazebo Dining Set",
        "slug": "garden-gazebo-dining-set",
        "product_type": "Outdoor Dining",
        "description": "Canopy gazebo with a wooden dining table and folding chairs, strung with lights.",
        "price": Decimal("2400000"),
        "image": "images/outdoor-gazebo-dining.jpg",
        "image_alt": "White canopy gazebo sheltering a wooden dining table and chairs on a deck",
    },
    {
        "name": "Wooden Picnic Bench Table",
        "slug": "wooden-picnic-bench-table",
        "product_type": "Outdoor Tables",
        "description": "Solid timber picnic table with attached benches.",
        "price": Decimal("950000"),
        "image": "images/outdoor-picnic-bench-table.jpg",
        "image_alt": "Wooden picnic table with bench seats on a gravel garden terrace with mountain views",
    },
    {
        "name": "Rattan Patio Dining Set for Four",
        "slug": "rattan-patio-dining-set-for-four",
        "product_type": "Outdoor Dining",
        "description": "Square patio table with four dark woven rattan chairs.",
        "price": Decimal("1850000"),
        "image": "images/outdoor-rattan-patio-dining.jpg",
        "image_alt": "Square patio table with four dark rattan chairs under a timber pergola",
    },
]


def forwards(apps, schema_editor):
    Product = apps.get_model("furnitureapp", "Product")
    for data in OUTDOOR_PRODUCTS:
        Product.objects.update_or_create(
            slug=data["slug"],
            defaults={**data, "room": "outdoor"},
        )


def backwards(apps, schema_editor):
    Product = apps.get_model("furnitureapp", "Product")
    Product.objects.filter(slug__in=[p["slug"] for p in OUTDOOR_PRODUCTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("furnitureapp", "0008_office_products"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
