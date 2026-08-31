"""
Django settings for the Restaurant Management System.

This is a single-restaurant, non-SaaS, non-multi-tenant system.
Secrets are never hardcoded — everything sensitive is read from
environment variables via python-dotenv.

Deployment target: Vercel. Locally (and anywhere DATABASE_URL isn't
set) this falls back to SQLite so `manage.py runserver` keeps working
with zero setup — production always uses Postgres via DATABASE_URL,
which you set yourself in the Vercel project's Environment Variables
(Vercel doesn't provision a database automatically the way some
platforms do — point it at Vercel Postgres, Neon, Supabase, or any
other Postgres provider's connection string).
"""

from pathlib import Path

import dj_database_url
from dotenv import load_dotenv
import os

# Load environment variables from .env at the project root.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    value = os.environ.get(key)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def env_list(key, default=""):
    value = os.environ.get(key, default)
    return [item.strip() for item in value.split(",") if item.strip()]


# ─────────────────────────────────────────────────────────────────────────
# CORE
# ─────────────────────────────────────────────────────────────────────────

SECRET_KEY = env("DJANGO_SECRET_KEY", "django-insecure-change-me-in-.env")

DEBUG = env_bool("DJANGO_DEBUG", True)

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")

# Vercel sets VERCEL_URL automatically for every deployment (the
# production domain, and a unique URL per preview deploy too) — added
# here so a fresh deploy behind Vercel's own domain works without
# manually copying that hostname into DJANGO_ALLOWED_HOSTS every time
# you deploy. A custom domain still needs to be added to
# DJANGO_ALLOWED_HOSTS (and CSRF_TRUSTED_ORIGINS below) explicitly.
VERCEL_URL = env("VERCEL_URL")
if VERCEL_URL:
    ALLOWED_HOSTS.append(VERCEL_URL)

CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "")
if VERCEL_URL:
    CSRF_TRUSTED_ORIGINS.append(f"https://{VERCEL_URL}")

# ─────────────────────────────────────────────────────────────────────────
# PRODUCTION SECURITY HARDENING
# ─────────────────────────────────────────────────────────────────────────
# All gated behind DEBUG so local development (DEBUG=True, plain
# http://127.0.0.1:8000) is completely unaffected — these only take
# effect once DJANGO_DEBUG=False is set in the production environment.

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7  # 1 week to start; raise once confirmed stable.
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # Vercel terminates TLS at its own edge network and forwards the
    # request to the function with this header set — without telling
    # Django to trust it, request.is_secure() is always False behind
    # the proxy, which would make SECURE_SSL_REDIRECT loop forever.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# ─────────────────────────────────────────────────────────────────────────
# APPLICATIONS
# ─────────────────────────────────────────────────────────────────────────

INSTALLED_APPS = [
    # Unfold must load before django.contrib.admin so its templates
    # take precedence — this restyles the built-in /admin/ only, and
    # doesn't touch the separate custom Dashboard app at all.
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "cloudinary_storage",
    "cloudinary",
    # Local apps
    "core",
    "accounts",
    "dashboard",
    "menu",
    "orders",
    "customers",
    "tables",
    "reports",
    "inventory",
    "storefront",
    "reservations",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.StaffAccessMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "storefront.context_processors.cart",
                "accounts.context_processors.staff_access",
                "core.context_processors.restaurant_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"


# ─────────────────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────────────────
# You set DATABASE_URL yourself in Vercel's Environment Variables for
# this project (Vercel doesn't provision a database automatically —
# point it at Vercel Postgres, Neon, Supabase, or another provider).
# Locally, DATABASE_URL is normally unset, so this falls
# back to SQLite — no local Postgres setup required for development.
# conn_max_age keeps connections alive between requests in production
# (pointless for SQLite, harmless to set either way).

DATABASE_URL = env("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=not DEBUG,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# ─────────────────────────────────────────────────────────────────────────
# PASSWORD VALIDATION
# ─────────────────────────────────────────────────────────────────────────

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ─────────────────────────────────────────────────────────────────────────
# INTERNATIONALIZATION
# ─────────────────────────────────────────────────────────────────────────

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True


# ─────────────────────────────────────────────────────────────────────────
# STATIC & MEDIA FILES
# ─────────────────────────────────────────────────────────────────────────

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise serves static files if a request ever reaches the Python
# function directly. On Vercel, vercel.json (see project root) routes
# /static/* straight to the pre-built static files at Vercel's edge
# instead, which is faster and doesn't spend a function invocation on
# serving a CSS file — WhiteNoise here is the fallback/local-dev path,
# not the primary one. Compressed + hashed filenames for cache-busting,
# with a manifest so a missing hashed file fails loudly in
# collectstatic rather than 404ing for visitors.
# (Only STATICFILES_STORAGE is set here, not the unified STORAGES
# dict — media storage already uses the legacy DEFAULT_FILE_STORAGE
# setting below for Cloudinary, and Django doesn't allow mixing the
# old per-purpose settings with the new STORAGES dict.)
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media (food images, etc.) is stored on Cloudinary rather than locally.
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": env("CLOUDINARY_CLOUD_NAME"),
    "API_KEY": env("CLOUDINARY_API_KEY"),
    "API_SECRET": env("CLOUDINARY_API_SECRET"),
}
DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

# Paystack (storefront online checkout). Secret key only — never exposed
# client-side; the checkout flow initializes transactions server-side
# and verifies both the callback and the webhook signature against it.
PAYSTACK_SECRET_KEY = env("PAYSTACK_SECRET_KEY", "")
MEDIA_URL = "media/"


# ─────────────────────────────────────────────────────────────────────────
# DEFAULT PRIMARY KEY FIELD TYPE
# ─────────────────────────────────────────────────────────────────────────

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ─────────────────────────────────────────────────────────────────────────
# AUTHENTICATION — Accounts app
# ─────────────────────────────────────────────────────────────────────────

# Points Django at the custom User model defined in accounts/models.py.
# Introduced in the Accounts phase, before any migrations exist, so it
# carries no migration-ordering risk.
AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "accounts:login"

# No real email provider is wired up yet — the "Forgot Password"
# structure is fully functional, but reset emails print to the
# console instead of being sent. Swap this for a real backend
# (e.g. SMTP) when email integration is added.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


# ─────────────────────────────────────────────────────────────────────────
# DJANGO UNFOLD — /admin/ theming only
# ─────────────────────────────────────────────────────────────────────────
# This restyles django.contrib.admin (site title/header still also set
# on admin.site in core/admin.py, which Unfold reads and displays).
# It does NOT touch the separate custom Dashboard app, and existing
# ModelAdmin registrations (with their StaffAccess permission mixins)
# are untouched — Unfold reskins the standard admin views regardless
# of which ModelAdmin base class they use.

UNFOLD = {
    "SITE_TITLE": "Lolaire's Kitchen Admin",
    "SITE_HEADER": "Lolaire's Kitchen",
    "SITE_SYMBOL": "restaurant",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "COLORS": {
        "primary": {
            "50": "250 245 236",
            "100": "241 227 200",
            "200": "230 202 154",
            "300": "216 175 112",
            "400": "192 141 59",
            "500": "171 118 42",
            "600": "143 99 33",
            "700": "112 77 26",
            "800": "80 55 19",
            "900": "48 33 11",
            "950": "17 12 4",
        },
    },
}
