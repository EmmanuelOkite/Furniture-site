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

## Update 2026-10-13: collection page, new images, prices

- **New images** (10 Pexels photos): bedroom suite → Bedroom category card; terrace banquette → Outdoor category card. The typographic "Photography coming soon" cards and their CSS were removed.
- **Collection page** `/collection/` (`views.collection`, `templates/collection.html`): every active product with image, room · type, name, description and price. Room filter chips use `?room=<code>`; unknown values fall back to all rooms; an empty room shows a message.
- **Links to the collection:** category cards (filtered by room), "View all categories", the "Explore Furniture" button, footer Rooms links, navbar and footer **Shop**. **Categories** now jumps to the homepage room cards (`/#categories`).
- **Products:** migration `0004` adds 13 products (the 8 remaining new photos plus one per room from the category photos) and gives all 17 a price. Product images are pre-cropped to 5:4 around the furniture (`static/images/product-*.jpg`).
- **Prices are placeholders** requested by the owner ("random prices from 100k UGX"), from UGX 185,000 to UGX 6,500,000. Edit them in the admin (the price is editable directly in the product list) before launch.
- **Homepage "Pieces You'll Love"** now renders products with the new `is_featured` flag (max 4) from the database through `includes/product_card.html`. The "Sample" badges and the "catalogue being prepared" note were removed now that prices are shown.
- **"View details"** links go to the product on the collection page (`/collection/?room=…#slug`), which highlights it. There is no separate product detail page.
- **Tests:** 15, all passing.

## Update 2026-10-13: Living Room page

- **New page** `/living-room/` (`views.living_room`, `templates/living_room.html`): a photo banner, the room filter buttons, and every active living room product, newest first, each with photo, details and UGX price.
- **Products:** migration `0005` adds 9 living room pieces from the new Pexels photos (`static/images/living-*.jpg`, pre-cropped to 5:4), priced UGX 700,000 to 5,800,000. The prices are placeholders.
- **Links:** every Living Room link goes to the new page: the homepage category card, footer Rooms, the room filter button on the Collection page, and "View details" on living room product cards (`Product.get_absolute_url`). `/collection/?room=living-room` redirects (302) to `/living-room/`, so old links still work.
- `Product.room_url()` decides which page lists a room, so a future room page only needs a change there.
- **Tests:** 19, all passing.

## Update 2026-10-13: Bedroom page and shared room pages

- **Bedroom page** `/bedroom/`: same layout as Living Room. Migration `0006` adds 9 bedroom pieces (`static/images/bedroom-*.jpg`), priced UGX 280,000 to 7,800,000 (placeholders). The page shows all 11 bedroom pieces, newest first.
- **Refactor:** Living Room and Bedroom now share one view (`views.room_page`) and one template (`templates/room_page.html`; `living_room.html` was removed). Each room's title, intro text and banner live in `furnitureapp/rooms.py` (`ROOM_PAGES`).
  - *Why:* copying the Living Room page would have meant two near-identical templates and views to keep in sync, and a third copy for each new room.
  - *To add another room page:* add an entry to `ROOM_PAGES`, add a `path()` in `furniture_site/urls.py`, and add a banner image. All links, redirects and "View details" anchors then follow automatically through `Product.room_url()`.
- **Links:** the homepage Bedroom card, footer Bedroom, and the Bedroom room filter button now go to `/bedroom/`. `/collection/?room=bedroom` redirects (302) there.
- **Tests:** 22, all passing.

## Open items

1. **Security:** `.env` is tracked in git (the `.gitignore` is inside `furniture_site/`, so it does not apply at the project root). Move `.gitignore` to the project root, untrack `.env`, and rotate any credentials it contained if it was ever pushed.
2. Remove the non-image files from `furniture_site/images/` (`.exe`, `.docx`, `.crdownload`). Do not commit that folder; the site uses `static/images/`.
3. ~~Replace the contact and social placeholders in `footer.html`~~ Done (2026-10-12): Instagram, Facebook and TikTok links, Kyanja, Kampala (Google Maps link), and phones 0751 526 014 / 0767 250 127. Brand renamed to "Sam's Stunning Furniture"; logo mark re-extracted from the new `image.png`. The cart button was removed from the navbar. No email address yet.
4. Add bedroom and outdoor photography.
5. Once a `Product` model exists, render the featured grid from the database.
