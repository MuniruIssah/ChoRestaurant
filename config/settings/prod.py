"""
Production settings for Restaurant Ordering & Delivery Management System.
Requires PostgreSQL (DATABASE_URL), strong DJANGO_SECRET_KEY, and configures Cloudinary & security headers.
"""
import os
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401, F403

DEBUG = False

if SECRET_KEY == "django-insecure-dev1-foundation-key-change-in-production":
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production.")

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise ImproperlyConfigured("DATABASE_URL (PostgreSQL) is required in production.")

DATABASES = {
    "default": parse_database_url(DATABASE_URL),
}
DATABASES["default"]["CONN_MAX_AGE"] = int(os.environ.get("DB_CONN_MAX_AGE", "600"))

# Cloudinary media storage in production
if CLOUDINARY_URL:
    INSTALLED_APPS = [*INSTALLED_APPS, "cloudinary_storage", "cloudinary"]
    STORAGES["default"] = {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    }

# Redis Channel Layer for Django Channels in production
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

# Redis Cache in production
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

# Production Security Headers (Architecture §8)
SECURE_SSL_REDIRECT = get_env_bool("SECURE_SSL_REDIRECT", True)
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
