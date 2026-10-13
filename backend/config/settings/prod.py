"""Production settings for Render deployment."""

from .base import *  # noqa: F403

DEBUG = False

# Allowed hosts configuration (auto-detects Render host and supports custom domains)
ALLOWED_HOSTS = env.list(  # noqa: F405
    "ALLOWED_HOSTS",
    default=[".onrender.com", "localhost", "127.0.0.1"],
)
render_host = env("RENDER_EXTERNAL_HOSTNAME", default="")  # noqa: F405
if render_host and render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_host)

# CORS configuration for Vercel and custom frontends
CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=False)  # noqa: F405
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])  # noqa: F405
CORS_ALLOWED_ORIGIN_REGEXES = env.list(  # noqa: F405
    "CORS_ALLOWED_ORIGIN_REGEXES",
    default=[r"^https:\/\/.*\.vercel\.app$"],
)

# SSL & Security (Render handles SSL at the load balancer)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Static files via WhiteNoise
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# Optional Redis Cache (falls back to locmem if not configured)
REDIS_URL = env("REDIS_URL", default="")  # noqa: F405
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
