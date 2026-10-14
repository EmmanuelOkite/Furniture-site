"""
Rooms that have their own page (banner + every product for that room).

To give another room a page: add an entry here keyed by its Product.Room value,
add a matching path() in furniture_site/urls.py, and add a banner image.
Rooms without an entry are listed on the collection page (/collection/?room=...).
"""

ROOM_PAGES = {
    "living-room": {
        "url_name": "living_room",
        "title": "Living Room",
        "intro": "Sofas, lounge sets, chairs and media units for the room where everyone gathers.",
        "meta_description": "Sofas, sofa sets, chairs and TV units for the living room from Sam's Stunning Furniture, Kyanja, Kampala.",
        "banner": "images/living-banner.jpg",
        "banner_alt": "Low grey lounge sofa and a round marble coffee table in a warm, softly lit living room",
    },
    "bedroom": {
        "url_name": "bedroom",
        "title": "Bedroom",
        "intro": "Beds, bedside tables and lighting for calm, restful rooms.",
        "meta_description": "Beds, bedroom sets, bedside tables and lamps from Sam's Stunning Furniture, Kyanja, Kampala.",
        "banner": "images/bedroom-banner.jpg",
        "banner_alt": "Charcoal upholstered headboard against a slatted timber wall lit by amber pendant lamps",
    },
    "dining-room": {
        "url_name": "dining_room",
        "title": "Dining Room",
        "intro": "Dining tables, chairs and sideboards for everyday meals and long evenings with family.",
        "meta_description": "Dining sets, tables, chairs and sideboards from Sam's Stunning Furniture, Kyanja, Kampala.",
        "banner": "images/dining-banner.jpg",
        "banner_alt": "Ivory sideboard with white vases and a bronze lamp against a charcoal wall beside a dining table",
    },
    "office": {
        "url_name": "office",
        "title": "Office Furniture",
        "intro": "Desks, meeting tables and chairs for home offices and workplaces that work as hard as you do.",
        "meta_description": "Office desks, boardroom tables and office chairs from Sam's Stunning Furniture, Kyanja, Kampala.",
        "banner": "images/office-banner.jpg",
        "banner_alt": "Oak boardroom table with black leather office chairs in a grey meeting room",
    },
}
