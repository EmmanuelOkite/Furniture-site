"""
Adds ten office pieces for the Office Furniture page.

Prices are placeholders requested by the site owner (from 100k UGX upwards).
Replace them with real prices in the admin before launch.
"""

from decimal import Decimal

from django.db import migrations

OFFICE_PRODUCTS = [
    {
        "name": "Oak Workstation Desk",
        "slug": "oak-workstation-desk",
        "product_type": "Desks",
        "description": "Long oak-top workstation desk with room for a laptop, monitor and storage shelf.",
        "price": Decimal("1200000"),
        "image": "images/office-oak-workstation-desk.jpg",
        "image_alt": "Oak workstation desk with a laptop and a potted cactus by a window",
    },
    {
        "name": "White Bench Desk System",
        "slug": "white-bench-desk-system",
        "product_type": "Desks",
        "description": "Modular white bench desks on steel frames, shown with black mesh task chairs.",
        "price": Decimal("4600000"),
        "image": "images/office-bench-desk-system.jpg",
        "image_alt": "White modular bench desks with black mesh office chairs in a bright open office",
    },
    {
        "name": "Open-Plan Workstation Row",
        "slug": "open-plan-workstation-row",
        "product_type": "Desks",
        "description": "Row of connected white workstations with black mesh ergonomic chairs.",
        "price": Decimal("3900000"),
        "image": "images/office-workstation-row.jpg",
        "image_alt": "Row of white workstations and black mesh chairs beside a glass partition",
    },
    {
        "name": "Executive Desk & Wingback Chair",
        "slug": "executive-desk-wingback-chair",
        "product_type": "Desks",
        "description": "Black executive desk with a cognac leather wingback reading chair.",
        "price": Decimal("3300000"),
        "image": "images/office-executive-desk-wingback.jpg",
        "image_alt": "Black executive desk and a cognac leather wingback chair in a teal-walled study",
    },
    {
        "name": "White Home Office Set",
        "slug": "white-home-office-set",
        "product_type": "Desks",
        "description": "Compact white desk with a matching drawer unit, side cabinet and mesh chair.",
        "price": Decimal("1750000"),
        "image": "images/office-white-home-office.jpg",
        "image_alt": "White desk, drawers and black mesh chair in a bright home office",
    },
    {
        "name": "Oak Boardroom Table & Leather Chairs",
        "slug": "oak-boardroom-table-leather-chairs",
        "product_type": "Meeting Tables",
        "description": "Oak boardroom table on a black base with black leather ribbed office chairs.",
        "price": Decimal("5400000"),
        "image": "images/office-live-edge-boardroom.jpg",
        "image_alt": "Oak boardroom table surrounded by black leather office chairs in a grey meeting room",
    },
    {
        "name": "Long Boardroom Table with Planter",
        "slug": "long-boardroom-table-planter",
        "product_type": "Meeting Tables",
        "description": "Extra-long pine boardroom table with a built-in planter and blue ergonomic chairs.",
        "price": Decimal("6200000"),
        "image": "images/office-boardroom-planter.jpg",
        "image_alt": "Long pine boardroom table with a central planter and blue ergonomic chairs",
    },
    {
        "name": "Oak Meeting Table & Wood-Shell Chairs",
        "slug": "oak-meeting-table-wood-shell-chairs",
        "product_type": "Meeting Tables",
        "description": "Oak meeting table for eight with curved wood-shell executive chairs.",
        "price": Decimal("4900000"),
        "image": "images/office-oak-meeting-table.jpg",
        "image_alt": "Oak meeting table with curved wood-shell chairs in a glass-walled meeting room",
    },
    {
        "name": "Trestle Writing Desk & Linen Chair",
        "slug": "trestle-writing-desk-linen-chair",
        "product_type": "Desks",
        "description": "Walnut-stained trestle writing desk with a cream linen side chair.",
        "price": Decimal("1450000"),
        "image": "images/office-trestle-writing-desk.jpg",
        "image_alt": "Walnut trestle writing desk with a cream linen chair in a traditional study",
    },
    {
        "name": "Chrome Executive Office Chair",
        "slug": "chrome-executive-office-chair",
        "product_type": "Office Chairs",
        "description": "High-back black leather office chair with a polished chrome frame.",
        "price": Decimal("650000"),
        "image": "images/office-chrome-executive-chair.jpg",
        "image_alt": "Rows of black leather high-back office chairs with chrome frames at white desks",
    },
]


def forwards(apps, schema_editor):
    Product = apps.get_model("furnitureapp", "Product")
    for data in OFFICE_PRODUCTS:
        Product.objects.update_or_create(
            slug=data["slug"],
            defaults={**data, "room": "office"},
        )


def backwards(apps, schema_editor):
    Product = apps.get_model("furnitureapp", "Product")
    Product.objects.filter(slug__in=[p["slug"] for p in OFFICE_PRODUCTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("furnitureapp", "0007_dining_room_products"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
