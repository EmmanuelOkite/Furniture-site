# Homepage Redesign — Decisions Log

Date: 2026-10-12
Scope: navbar, homepage, footer. No new pages, routes, models or dependencies.

## Files

| File | Change |
|---|---|
| `templates/base.html` | Fonts, stylesheet, favicon, skip link, navbar + footer includes, `body_class` block, `main.js` |
| `templates/includes/navbar.html` | Sticky header, nav links, search panel, account, cart badge, mobile menu toggle |
| `templates/includes/footer.html` | New: brand, quick links, rooms, contact placeholders, social placeholders |
| `templates/home.html` | Hero, categories, featured pieces, brand story, call to action |
| `static/css/main.css` | New: complete design system and responsive layout |
| `static/js/main.js` | New: header scroll state, mobile menu, search panel (no libraries) |
| `static/images/*` | New: 12 web-optimised images (~1.2 MB total, from ~30 MB of originals) |
| `furniture_site/settings.py` | Added `STATICFILES_DIRS = [BASE_DIR / "static"]` |

## Design decisions

- **Palette:** ivory `#f7f3ec`, sand `#efe8dc`, forest green `#2f4a3a` (buttons, active nav, call to action), walnut `#7a5234` (labels), charcoal `#262622` (text). Defined once as CSS variables in `main.css`.
- **Type:** Cormorant Garamond (headings) + Jost (body/UI) via Google Fonts, with Georgia / system-font fallbacks if Google Fonts is unreachable.
- **Hero:** a full-screen photo with the text over its darker left side. The header is transparent over the hero and turns solid ivory on scroll. The `<img>` uses `srcset` (1200 / 2400 px) rather than a CSS background, so it has alt text and loads at the right size.
- **Categories:** an asymmetric (bento) grid. The source folder had **no bedroom or outdoor photos**, so those two cards are typographic and labelled "Photography coming soon" rather than using unrelated images.
- **Featured pieces:** there is no `Product` model, so the four cards are labelled **Sample**, show "Price coming soon", and the section says the catalogue is in preparation. No favourite/heart button was added, because there is no wishlist feature behind it.
- **Brand story:** copy avoids claims about manufacturing, delivery, warranties or quality.
- **Links:** everything without a route is `#`. "Explore Collection", "Discover Our Story" and "Explore Furniture" scroll to sections on the homepage, so they work today.
- **Search:** the search panel opens and closes, but submitting only reloads the page with `?q=`, because no search view exists yet.

## Image mapping (originals in `furniture_site/images/`)

| Static file | Source |
|---|---|
| hero-living-room(-1200).jpg | kam-idris (yellow armchair) |
| category-living-room.jpg | costa-live |
| category-dining-room.jpg | anand-kumar |
| category-office.jpg | hannah-busing |
| product-velvet-sofa.jpg | phillip-goldsberry |
| product-leather-sofa.jpg | personalgraphic-com |
| product-boucle-chair.jpg | kevin-shek |
| product-tufted-chair.jpg | daniil-silantev |
| story-living-room.jpg | minh-pham |
| detail-wood-table.jpg | mahbod-akhzami |

Not used: ambo-ampeng, inside-weather, sven-brandsma, virender-singh (style or colour mismatch) and the duplicate "(1)" files. All are Unsplash photos; credit the photographers on an About page if possible.

## Verification performed

- `manage.py check`: no issues.
- `/` and `/admin/login/` return 200 with `DEBUG=True` and with `DEBUG=False` after `collectstatic` (WhiteNoise manifest hashing works; all 14 static references resolve).
- Screenshots at 1440, 820, 390 and 360 px wide: no horizontal scrolling; the mobile menu and search panel open correctly.
- No browser console errors from the site.

## Update 2026-10-12: logo and search

**Logo.** The gold monogram was cut out of `furniture_site/images/image.png` with a transparent background and saved as `static/images/logo-mark.png`. It sits beside the existing text name in the navbar. The full logo (monogram plus navy wordmark on paper) was rejected for the navbar for three reasons: the lettering is unreadable at navbar height, navy disappears on the dark hero, and the paper background would show as a box. At 340px wide and below, only the mark is shown.

**Navbar icons.** No notifications button existed. The user chose to keep Search, Account and Cart unchanged.

**Product model** (`furnitureapp/models.py`). Fields: name, slug, room (Living Room / Bedroom / Dining Room / Office / Outdoor), product_type, description, price (optional, shows "Price coming soon"), image, image_alt, is_sample, is_active and timestamps. Registered in the admin. Migration `0002_sample_products` adds the four homepage samples with `is_sample=True`; reversing it removes them.
- `image` is a **static file path**, not an upload (`ImageField`), on purpose: uploads need Pillow and persistent media storage, and Render's disk is wiped on every deploy. Switch to `ImageField` once a storage service (e.g. S3 or Cloudinary) is chosen. The model validates that the path exists.
- Price has no currency symbol yet, because the currency is still an open question.

**Search** (`/search/?q=…`, `views.search`):
- Every word in the query must match at least one of name, type, description or room label (case-insensitive). So "green sofa" finds the velvet sofa and "green bed" finds nothing.
- Only `is_active` products are searched.
- Queries are trimmed and capped at 100 characters. Results show 12 per page. A blank query shows only the search form; no matches shows a "Nothing matched" message.
- Uses `icontains` (SQL `ILIKE`). That is fine for a catalogue of hundreds of products; consider PostgreSQL full-text search if it grows into the thousands.

**Tests** (`furnitureapp/tests.py`): 9 tests covering matching, multi-word queries, room labels, inactive products, the empty state, a blank query and HTML escaping. All pass.

**Homepage featured cards** are still hard-coded in `home.html`. Next step: render them from `Product` using `includes/product_card.html`.

## Open items

1. **Security:** `.env` is tracked in git (the `.gitignore` is inside `furniture_site/`, so it does not apply at the project root). Move `.gitignore` to the project root, untrack `.env`, and rotate any credentials it contained if it was ever pushed.
2. Remove the non-image files from `furniture_site/images/` (`.exe`, `.docx`, `.crdownload`). Do not commit that folder; the site uses `static/images/`.
3. Replace the contact and social placeholders in `footer.html` with real details.
4. Add bedroom and outdoor photography.
5. Once a `Product` model exists, render the featured grid from the database.
