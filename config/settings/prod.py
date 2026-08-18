from .base import *  # noqa: F401,F403

DEBUG = False

# ALLOWED_HOSTS must be set explicitly via the environment in production —
# no wildcard default.
if not ALLOWED_HOSTS:
    raise RuntimeError("ALLOWED_HOSTS must be set via the environment in production")

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
