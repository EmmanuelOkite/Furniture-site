"""Adds the four sample pieces shown on the homepage, marked is_sample=True."""

from django.db import migrations

SAMPLE_PRODUCTS = [
    {
        "name": "Velvet Three-Seater Sofa",
        "slug": "velvet-three-seater-sofa",
        "room": "living-room",
        "product_type": "Sofas",
        "description": "Forest-green velvet sofa with bolster cushions and tapered wooden legs.",
        "image": "images/product-velvet-sofa.jpg",
        "image_alt": "Forest-green velvet three-seater sofa with bolster cushions and tapered wooden legs",
    },
    {
        "name": "Tufted Leather Sofa",
        "slug": "tufted-leather-sofa",
        "room": "living-room",
        "product_type": "Sofas",
        "description": "Cognac brown leather sofa with deep button tufting and wooden legs.",
        "image": "images/product-leather-sofa.jpg",
        "image_alt": "Cognac leather sofa with deep button tufting and wooden legs",
    },
    {
        "name": "Rounded Bouclé Lounge Chair",
        "slug": "rounded-boucle-lounge-chair",
        "room": "living-room",
        "product_type": "Chairs",
        "description": "Rounded cream boucle armchair on a low metal swivel base.",
        "image": "images/product-boucle-chair.jpg",
        "image_alt": "Rounded cream bouclé lounge chair on a low metal base",
    },
    {
        "name": "Tufted Accent Chair",
        "slug": "tufted-accent-chair",
        "room": "bedroom",
        "product_type": "Accent Chairs",
        "description": "Ivory button-tufted accent chair with turned white legs.",
        "image": "images/product-tufted-chair.jpg",
        "image_alt": "Ivory button-tufted accent chair with turned white legs",
    },
]


def add_samples(apps, schema_editor):
    Product = apps.get_model("furnitureapp", "Product")
    for data in SAMPLE_PRODUCTS:
        Product.objects.update_or_create(
            slug=data["slug"],
            defaults={**data, "is_sample": True},
        )


def remove_samples(apps, schema_editor):
    Product = apps.get_model("furnitureapp", "Product")
    Product.objects.filter(
        slug__in=[p["slug"] for p in SAMPLE_PRODUCTS],
        is_sample=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("furnitureapp", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_samples, remove_samples),
    ]
