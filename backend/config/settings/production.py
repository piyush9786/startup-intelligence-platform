import os

from django.core.exceptions import ImproperlyConfigured

from .base import *

DEBUG = False


_WEAK_SECRET_VALUES = {
    "",
    "changeme",
    "change-me",
    "password",
    "startup",
    "minioadmin",
    "unsafe-development-key",
}


def _required_secret(name: str, *, minimum_length: int = 12) -> str:
    value = os.environ.get(name, "").strip()
    if (
        len(value) < minimum_length
        or value.lower() in _WEAK_SECRET_VALUES
    ):
        raise ImproperlyConfigured(
            f"{name} must be set to a non-placeholder value of at least "
            f"{minimum_length} characters in production."
        )
    return value


SECRET_KEY = _required_secret("DJANGO_SECRET_KEY", minimum_length=32)
DATABASES["default"]["PASSWORD"] = _required_secret("POSTGRES_PASSWORD")
NEO4J_PASSWORD = _required_secret("NEO4J_PASSWORD")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "").strip()
if not MINIO_ACCESS_KEY:
    raise ImproperlyConfigured(
        "MINIO_ACCESS_KEY must be set in production."
    )
MINIO_SECRET_KEY = _required_secret("MINIO_SECRET_KEY")

ALLOWED_HOSTS = [
    value.strip()
    for value in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if value.strip()
]
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must contain at least one production host."
    )

# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# HTTPS & HSTS Hardening
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Harden JWT
SIMPLE_JWT["AUTH_COOKIE_SECURE"] = True
SIMPLE_JWT["AUTH_COOKIE_HTTP_ONLY"] = True

# Production Structured Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "production": {
            "format": "%(asctime)s [%(levelname)s] %(name)s (%(process)d:%(thread)d): %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "production",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
