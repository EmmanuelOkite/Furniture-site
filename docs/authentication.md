# Accounts & Authentication

How sign-up, sign-in and account management work on the site, how to run and
deploy them, and which security protections are (and are not) in place.
Design decisions and the alternatives considered are in
[auth-decisions.md](auth-decisions.md).

## 1. What users can do

| Page | URL | Notes |
|------|-----|-------|
| Register | `/accounts/register/` | Name, email, optional phone, password + confirmation. No email verification: the account can sign in straight away (decision D13). |
| Sign in | `/accounts/login/` | Email + password, "keep me signed in", then a 2FA code if enabled. |
| Forgot / reset password | `/accounts/password/reset/` | Reset links last 1 h and work once; all sessions end afterwards. |
| Profile | `/accounts/profile/` | Edit first name, last name, phone. Shows email status, role, join date, last sign-in. |
| Change password | `/accounts/password/change/` | Needs the current password; other sessions end. |
| Security | `/accounts/security/` | 2FA, signed-in devices (sign out one or all), recent activity, deactivate/delete. |
| Two-factor | `/accounts/security/two-factor/…` | Authenticator app (QR code or key) + 10 single-use backup codes. |
| Deactivate / reactivate | `/accounts/deactivate/`, `/accounts/reactivate/` | Self-deactivated accounts can be reactivated by an emailed link. |
| Delete account | `/accounts/delete/` | Password + typing DELETE. Removes the user and their audit data. |

Staff and administrators use the Django admin at `/admin/`. Its sign-in
redirects to `/accounts/login/`, so the admin gets the same throttling,
lockout and 2FA.

## 2. Code map

```
accounts/
  models.py        User (email login), PasswordHistory, SecurityEvent, UserSession,
                   RateLimit, LoginLockout, TOTPDevice, BackupCode
  roles.py         Role definitions -> Django Groups; set_role(); privilege-escalation rules
  services.py      Sign-in steps (credentials, lockout, 2FA hand-off, session tracking)
  throttling.py    Database-backed rate limits and progressive lockout
  tokens.py        Signed single-use tokens (reactivation links)
  twofactor.py     TOTP + backup codes (the only module that knows about 2FA)
  sessions.py      List / revoke a user's sessions
  validators.py    Email normalisation, phone validation, PasswordHistoryValidator
  emails.py        Sending account emails (failures logged, never shown)
  security.py      Client IP, keyed hashing, audit logging
  forms.py views.py urls.py admin.py
  management/commands/prune_account_records.py   retention clean-up
  tests/           94 tests (run alongside the 25 catalogue tests)
templates/accounts/          pages; templates/accounts/emails/ plain-text emails
templates/403.html 404.html 500.html 403_csrf.html   generic error pages
static/css/accounts.css  static/js/accounts.js
```

## 3. Roles and permissions

| Role | Admin access | Permissions |
|------|--------------|-------------|
| Customer (default) | No | None: manages only their own account through `/accounts/` pages |
| Staff | Yes | View, add and change products |
| Administrator | Yes | Products (incl. delete), view/change users, assign roles, read the security log |
| Superuser | Yes | Everything; the only one who can grant Administrator or superuser |

Rules enforced on the server (tested):
- Nobody can change their own role or deactivate themselves from the admin.
- Administrators can move users between Customer and Staff only. They cannot edit
  superusers or other Administrators, and cannot set anyone's password (they
  ask the user to use "Forgot password").
- `is_staff` follows the role automatically.
- Role definitions live in `accounts/roles.py` and are re-applied after every
  `migrate`, so edit the code, not the groups in the admin.

## 4. Running locally

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env              # then fill in values
python manage.py migrate
python manage.py createsuperuser    # asks for email, first and last name
python manage.py runserver
```

Emails (password reset, reactivation, alerts) are only printed in the terminal
running `runserver` while `DJANGO_EMAIL_BACKEND` is the console backend. They
are not delivered until SMTP settings are configured.

Run the tests: `python manage.py test` (PostgreSQL user needs permission to create the test database).

## 5. Deploying to Render: required steps

1. **Reset the production database once.** The project switched to a custom user
   model, so the existing tables can't be migrated in place (agreed: no
   production data to keep). Connect with `psql` and run
   `DROP SCHEMA public CASCADE; CREATE SCHEMA public;`, then make sure the
   deploy runs `python manage.py migrate`, then `python manage.py createsuperuser`
   from the Render shell. Products are recreated by the data migrations.
2. **Set environment variables:** `DJANGO_SECRET_KEY` (new random value),
   `DJANGO_DEBUG=False` (now also the default), `DJANGO_ALLOWED_HOSTS`, and the
   SMTP settings (`DJANGO_EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`,
   `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`). Add
   `DJANGO_CSRF_TRUSTED_ORIGINS` for any custom domain.
   The app now **refuses to start** without a secret key when debug is off.
3. **Set `DJANGO_TRUSTED_PROXY_COUNT` correctly.** I could not confirm how many
   proxies Render puts in front of the app. With the wrong value, either every
   visitor shares one IP (per-IP limits then lock everyone out together) or
   clients can forge their IP. After deploying, sign in and check the IP shown on
   the Security page: if it isn't your real public IP, set the value to `1` and check again.
4. **Schedule the clean-up** daily, e.g. a Render cron job running
   `python manage.py prune_account_records`. It deletes at most 5,000 rows per
   table per run and says so when a backlog remains.
5. **HSTS:** starts at 30 days. Once HTTPS is confirmed on every host, raise
   `DJANGO_SECURE_HSTS_SECONDS` to `31536000`; only enable subdomains/preload if
   every subdomain is HTTPS-only.
6. Open the Django admin once in a browser after deploy and check the browser
   console for Content-Security-Policy errors (not covered by automated tests).

## 6. Privacy (GDPR) notes

The system stores names, email addresses, phone numbers, IP addresses and
browser user-agents. To keep this proportionate:
- Security events and session records are deleted after 90 days
  (`ACCOUNTS_SECURITY_EVENT_RETENTION_DAYS`).
- Throttle and lockout tables store only HMACs, never raw emails or IPs.
- Deleting an account removes the user's profile, sessions, 2FA data, password
  history and audit events. The deletion is logged by user id only.
- Logs contain user ids and IPs, never passwords, tokens, session keys or email addresses.

The site's privacy notice should mention these data and retention periods.

## 7. Security checklist

Legend: ✅ implemented and covered by automated tests · ☑️ implemented, verified by configuration/`check --deploy` but not by a behavioural test · ❌ not implemented / known limitation

### Accounts and authentication
| Protection | Status |
|---|---|
| Custom user model, email as login, case-insensitive unique email (+ DB constraint) | ✅ |
| Email normalised before saving and lookup | ✅ |
| Server-side validation of all sign-up fields; frontend validation as a convenience | ✅ |
| Passwords hashed with Django's PBKDF2 hasher; never emailed or logged | ✅ |
| Password rules: min 12 chars, not common, not numeric-only, not similar to name/email | ✅ |
| Password history: last 5 passwords (and current) can't be reused | ✅ |
| Duplicate email rejected at registration (form + database constraint) | ✅ |
| Password reset and reactivation responses identical for unknown emails | ✅ |
| Generic sign-in error for wrong password, unknown email and inactive account | ✅ |
| Session key rotated on sign-in (session fixation) | ✅ |
| Progressive lockout per email (5 failures → 1, 2, 4… min, max 1 h), also for unknown emails | ✅ |
| Rate limits: sign-in, registration, password reset, reactivation, 2FA, password re-entry | ✅ |
| Logout is POST-only and deletes the server-side session | ✅ |
| Password change keeps current session, ends all others, emails the user | ✅ |
| Password reset: 1 h single-use token, token removed from URL, ends all sessions, clears lockout | ✅ |
| Optional TOTP 2FA with replay protection and single-use hashed backup codes | ✅ |
| Session list with per-device and "everywhere else" sign-out (IDOR-safe) | ✅ |
| New-network sign-in email alert; failed/locked/2FA events logged as warnings | ✅ |
| Account deactivation (self) and email reactivation; admin suspension can't be self-reversed | ✅ |
| Account deletion with password + typed confirmation | ✅ |
| "Keep me signed in" (14 days) vs. browser-session cookies | ✅ |

### Authorisation
| Protection | Status |
|---|---|
| RBAC with Django Groups; least-privilege role definitions | ✅ |
| Users can't change own role; only superusers grant Administrator/superuser | ✅ |
| Administrators can't edit superusers/Administrators or set passwords | ✅ |
| Profile form whitelists fields (no mass assignment of email/role/status) | ✅ |
| Objects always scoped to `request.user` (no IDOR) | ✅ |
| Admin sign-in goes through throttled, 2FA-aware login | ✅ |

### Web and production
| Protection | Status |
|---|---|
| CSRF protection on all forms (tested with enforced checks) | ✅ |
| XSS: template auto-escaping (tested) + Content-Security-Policy with script nonce | ✅ |
| Clickjacking: `X-Frame-Options: DENY` + CSP `frame-ancestors 'none'` | ✅ |
| `nosniff`, `Referrer-Policy: same-origin`, `Cross-Origin-Opener-Policy` | ✅ |
| Account pages sent with `Cache-Control: no-cache, no-store` | ✅ |
| SQL injection: ORM only, no raw SQL in the app | ☑️ |
| `DEBUG` off by default; app refuses to start without `SECRET_KEY` in production | ☑️ |
| Secure + HttpOnly session/CSRF cookies, SameSite=Lax, SSL redirect, HSTS (30 days) | ☑️ (`check --deploy`) |
| `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SECURE_PROXY_SSL_HEADER` from environment | ☑️ |
| No credentials in code; `.env` actually git-ignored (was broken by UTF-16 `.gitignore`) | ☑️ |
| Generic 403/404/500/CSRF error pages; sensitive POST fields hidden from error reports | ☑️ |
| Security event log with 90-day retention and capped clean-up command | ✅ |

### Not implemented / known limitations
| Item | Why / what to do |
|---|---|
| ❌ Profile pictures | Deferred until object storage is chosen (Render's disk is wiped on deploy). Then: Pillow + django-storages, validate type with Pillow (not the file extension), cap size at ~2 MB, re-encode the image. |
| ❌ Email verification | Removed at the owner's request (decision D13). Anyone can register with an address they don't own; the owner can recover it with "Forgot password". The sign-up form says when an email is already registered. |
| ❌ REST API / DRF and CORS | Not needed: the site is server-rendered on one origin. |
| ❌ Changing email address | Users contact the shop; a self-service flow needs re-verification of the new address. |
| ❌ TOTP secrets encrypted at rest | Stored in plain text in the database. Anyone with database access could generate codes (they would still need the password). |
| ❌ Breached-password check (e.g. Have I Been Pwned) | Only Django's built-in list of 20,000 common passwords is used. |
| ❌ CAPTCHA | Rate limits only; add one if automated sign-ups appear. |
| ⚠️ Timing of password-reset responses | Emails are sent synchronously, so a request for a real account takes slightly longer than one for an unknown address. Fix with a background email queue. |
| ⚠️ Lockout can be triggered by others | Someone who knows a customer's email can lock their sign-in for up to 1 hour. Mitigation: the customer can still reset their password, which clears the lockout. |
| ⚠️ Per-IP limits depend on `DJANGO_TRUSTED_PROXY_COUNT` | See deployment step 3. |
| ⚠️ CSP allows inline styles | Needed by the Django admin; scripts are still restricted. |
| ⚠️ Admin under CSP not browser-tested | See deployment step 6. |
| ⚠️ No external alerting | Events go to the database and console log; connect logs to monitoring if available. |
