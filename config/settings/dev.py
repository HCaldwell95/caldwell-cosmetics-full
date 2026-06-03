from .base import *

DEBUG = True

ALLOWED_HOSTS = [
    "127.0.0.1", 
    "localhost",
    ".herokuapp.com",
    "*",
]

# --------------------------------------------------
# EMAIL (console)
# --------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# --------------------------------------------------
# DEBUG TOOLS (optional)
# --------------------------------------------------

# INSTALLED_APPS += ["debug_toolbar"]
# MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")

INTERNAL_IPS = ["127.0.0.1"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}