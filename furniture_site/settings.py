"""
Django settings for furniture_site project.

Supports local development and deployment to Render.
"""

from pathlib import Path
import os
import sys

from django.core.exceptions import ImproperlyConfigured
from django.utils.csp import CSP

import environ
import dj_database_url


# --------------------------------------------------
# Base directory and environment variables
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()

# Load local environment variables from .env.
# Render environment variables are also read automatically
# from the hosting environment.
environ.Env.read_env(BASE_DIR / ".env")


# --------------------------------------------------
# Security settings
# --------------------------------------------------

# Production is the safe default: debug mode must be switched on explicitly.
DEBUG = env.bool("DJANGO_DEBUG", default=False)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off.")
    SECRET_KEY = "django-insecure-local-development-only"

# Old keys, comma-separated, still accepted for sessions and links while rotating SECRET_KEY.
SECRET_KEY_FALLBACKS = env.list("DJANGO_SECRET_KEY_FALLBACKS", default=[])

ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1"],
)

# Render provides this variable for the deployed web service.
render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME")

if render_hostname:
    ALLOWED_HOSTS.append(render_hostname)

# Origins allowed to submit forms over HTTPS, e.g. https://www.example.com
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
if render_hostname:
    CSRF_TRUSTED_ORIGINS.append(f"https://{render_hostname}")


# --------------------------------------------------
# Application definition
# --------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "furnitureapp",
]

AUTH_USER_MODEL = "accounts.User"


# --------------------------------------------------
# Middleware
# --------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# --------------------------------------------------
# URLs and templates
# --------------------------------------------------

ROOT_URLCONF = "furniture_site.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.csp",
            ],
        },
    },
]

WSGI_APPLICATION = "furniture_site.wsgi.application"


# --------------------------------------------------
# Database configuration
# --------------------------------------------------
# Render: use DATABASE_URL.
# Local development: use PostgreSQL settings from .env.

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME"),
            "USER": env("DB_USER"),
            "PASSWORD": env("DB_PASSWORD"),
            "HOST": env("DB_HOST", default="127.0.0.1"),
            "PORT": env("DB_PORT", default="5432"),
        }
    }


# --------------------------------------------------
# Password validation
# --------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
    {
        "NAME": "accounts.validators.PasswordHistoryValidator",
        "OPTIONS": {"history": 5},
    },
]

# Tests only: a fast hasher keeps the suite quick. Never used when serving requests.
TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"
if TESTING:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


# --------------------------------------------------
# Authentication, sessions and accounts
# --------------------------------------------------

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:profile"
LOGOUT_REDIRECT_URL = "home"

# Sessions end when the browser closes, or after 14 days with "Keep me signed in".
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True  # templates use the form token; no JavaScript reads the cookie
CSRF_COOKIE_SAMESITE = "Lax"

PASSWORD_RESET_TIMEOUT = 60 * 60  # reset links work for 1 hour

ACCOUNTS_SITE_NAME = "Sam's Stunning Furniture"
ACCOUNTS_TOTP_ISSUER = ACCOUNTS_SITE_NAME
ACCOUNTS_REACTIVATION_TIMEOUT = 60 * 60 * 24
ACCOUNTS_TWO_FACTOR_TIMEOUT = 60 * 5  # time allowed between password and code
ACCOUNTS_REMEMBER_ME_AGE = SESSION_COOKIE_AGE

# Progressive lockout per email: 5 failures -> 1 min, then 2, 4, 8 ... capped at 1 hour.
ACCOUNTS_LOCKOUT_THRESHOLD = 5
ACCOUNTS_LOCKOUT_BASE_SECONDS = 60
ACCOUNTS_LOCKOUT_MAX_SECONDS = 60 * 60
ACCOUNTS_LOCKOUT_RESET_SECONDS = 60 * 60 * 24  # failures are forgotten after a quiet day

# (max requests, window in seconds). ":ip" is per client IP, ":id" per email/account.
ACCOUNTS_RATE_LIMITS = {
    "login:ip": (30, 15 * 60),
    "register:ip": (10, 60 * 60),
    "password_reset:ip": (10, 60 * 60),
    "password_reset:id": (3, 60 * 60),
    "reactivate:ip": (10, 60 * 60),
    "reactivate:id": (3, 60 * 60),
    "two_factor:ip": (30, 15 * 60),
    "two_factor:id": (5, 5 * 60),
    "confirm_password:id": (10, 15 * 60),
}

# Number of reverse proxies in front of the app that append to X-Forwarded-For.
# 0 = use REMOTE_ADDR only. Set this correctly for your host, or every visitor
# shares the proxy's IP address and the per-IP limits apply to everyone together.
ACCOUNTS_TRUSTED_PROXY_COUNT = env.int("DJANGO_TRUSTED_PROXY_COUNT", default=0)

ACCOUNTS_SECURITY_EVENT_RETENTION_DAYS = env.int("ACCOUNTS_SECURITY_EVENT_RETENTION_DAYS", default=90)
ACCOUNTS_PRUNE_BATCH_SIZE = 5000


# --------------------------------------------------
# Internationalization
# --------------------------------------------------

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Africa/Kampala"

USE_I18N = True

USE_TZ = True


# --------------------------------------------------
# Static files
# --------------------------------------------------

STATIC_URL = "static/"

# Project-level assets (CSS, JavaScript, images) live in /static.
STATICFILES_DIRS = [BASE_DIR / "static"]

STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


# --------------------------------------------------
# Email
# --------------------------------------------------
# Local development prints emails to the console. In production set
# DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend and the
# EMAIL_* variables for your provider.

EMAIL_BACKEND = env("DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Sam's Stunning Furniture <no-reply@localhost>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL


# --------------------------------------------------
# Production security
# --------------------------------------------------

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Content Security Policy: only this site's scripts (plus a per-request nonce
# for the one inline script) and Google Fonts. Inline style attributes are
# allowed because the Django admin uses them.
SECURE_CSP = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF, CSP.NONCE],
    "style-src": [CSP.SELF, CSP.UNSAFE_INLINE, "https://fonts.googleapis.com"],
    "font-src": [CSP.SELF, "https://fonts.gstatic.com"],
    "img-src": [CSP.SELF, "data:"],
    "object-src": [CSP.NONE],
    "base-uri": [CSP.SELF],
    "form-action": [CSP.SELF],
    "frame-ancestors": [CSP.NONE],
}

if not DEBUG:
    # Render (and most hosts) end HTTPS at a proxy that sets X-Forwarded-Proto.
    # Only enable this behind a proxy that overwrites the header.
    if env.bool("DJANGO_BEHIND_HTTPS_PROXY", default=bool(render_hostname)):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Start with a short HSTS max-age, then raise it to a year (31536000)
    # once HTTPS is confirmed working everywhere.
    SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)
    SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=False)


# --------------------------------------------------
# Logging
# --------------------------------------------------
# Security events are logged by user id and IP; passwords, tokens, session
# keys and email addresses are never written to the log.

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "{asctime} {levelname} {name} {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "loggers": {
        "accounts.security": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
if TESTING:
    LOGGING["loggers"]["accounts.security"]["level"] = "CRITICAL"


# --------------------------------------------------
# Default primary key
# --------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
