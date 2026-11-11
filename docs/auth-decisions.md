# Authentication & Accounts: Decision Record

Status: accepted, 2026-11-11. Covers the `accounts` app (custom user model, sign-up,
email verification, login, password management, roles, profile, account security).

## Context (state of the project before this work)

- Django 6.1, server-rendered templates, PostgreSQL, deployed on Render.
- Django's default `auth.User` was already migrated; the only user was one superuser.
- No REST API, no cache backend, no media storage (Render's disk is wiped on deploy).
- `.gitignore` was saved as UTF-16, so git ignored nothing and `.env` was at risk of being committed.

## Decisions

| # | Decision | Alternatives considered | Why |
|---|----------|-------------------------|-----|
| D1 | **Custom `accounts.User`, email as the login identifier, no username.** Database reset to adopt it. | In-place migration of `auth_user`. | Project owner confirmed no production data must be kept. A reset is the documented, low-risk path; product data is recreated by the catalogue's data migrations. |
| D2 | **Session authentication with Django templates; no Django REST Framework.** | DRF with token/JWT auth. | The site is server-rendered and has no API consumer. An API would add a second attack surface (token storage, CORS) for no benefit. Sessions get Django's CSRF protection, HttpOnly cookies and server-side revocation. |
| D3 | **Roles are Django Groups** (Administrator, Staff, Customer) created by a data migration, with the permission `accounts.assign_role` controlling who can change roles. | Role field on the user; custom permission tables. | Uses Django's tested permission system and the admin. Only superusers can create Administrators or grant superuser status; nobody can change their own role. |
| D4 | **Rate limits and lockouts are stored in the database**, keyed by an HMAC of the IP or email. | Cache-based limits (LocMem/Redis); django-axes/django-ratelimit. | There is no shared cache. LocMem is per process, so gunicorn workers would each keep their own count, and it resets on restart. The database needs no new infrastructure. HMAC keys mean raw emails/IPs are never stored in throttle tables, and lockouts apply to unknown emails too, so they cannot be used to discover accounts. |
| D5 | **Password reset uses Django's built-in views and token generator; reactivation (originally also email verification) uses `django.core.signing` with a state fingerprint.** | One generator for everything. | Django's generator has a single global timeout (`PASSWORD_RESET_TIMEOUT`). Signed tokens allow a separate lifetime per purpose. The fingerprint (verification state / active state) makes every link single-use. |
| D6 | **Password history validator** (last 5) plugged into `AUTH_PASSWORD_VALIDATORS`. | Custom checks inside each form. | Django calls validators from every password-setting path (sign-up, change, reset, admin) and calls `password_changed()` after saving, so a single class covers every path. |
| D7 | **Optional TOTP 2FA with `pyotp` + `segno`** (pure-Python SVG QR code), with one-time backup codes. | Hand-written TOTP; SMS; defer. | Small, well-established libraries; SMS is weaker (SIM swap). Kept in `accounts/twofactor.py` so the login view only asks "does this user need a second step?". |
| D8 | **No profile pictures in this version.** | Local media; S3/Cloudinary. | Render's disk is wiped on deploy and no object storage is chosen yet. See "Future work" in `docs/authentication.md`. |
| D9 | **Unknown-email responses are generic** for sign-in, password reset and reactivation. *Registration changed by D13.* | "Email already registered" error everywhere. | Public responses should not reveal which emails are registered. |
| D10 | **Built-in CSP (Django 6) with a nonce** for the one inline script. | No CSP; third-party CSP package. | Defence in depth against XSS at no dependency cost. |
| D11 | **Security events in one `SecurityEvent` table** (login success/failure, password changes, 2FA, role changes…), pruned after a retention period by a management command with a batch cap. | Separate login-activity and audit tables. | One indexed table answers "what happened to this account". IPs are personal data under GDPR, so retention is limited (default 90 days). |
| D12 | **Emails are sent synchronously** through the configured SMTP backend. | Celery/RQ worker. | No queue infrastructure exists. Send failures are logged and the user still sees the generic response. |
| D13 | **No email verification (2026-11-11, project owner's decision).** New accounts can sign in immediately. Registering with an existing email shows "An account with this email address already exists". `email_verified_at` is kept and set when someone completes a password reset (that proves they own the inbox). | Keep verification (the original design) and fix email delivery. | The owner wants sign-up without an inbox step. **Accepted risks:** someone can register with an address they don't own (the real owner can take it back with "Forgot password"); and the sign-up form reveals whether an email is registered, which is limited by the registration rate limit (10 per IP per hour). |
