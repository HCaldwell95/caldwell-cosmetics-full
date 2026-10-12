from .base import *

DEBUG = False

ALLOWED_HOSTS = [
    "caldwellcosmetics.co.uk",
    "www.caldwellcosmetics.co.uk",
    "caldwell-cosmetics-django-241f71271e98.herokuapp.com",
    ".herokuapp.com",
    ".onrender.com",
]

DATABASES = {
    "default": dj_database_url.config(
        conn_max_age=600,
        ssl_require=True,
    )
}

# --------------------------------------------------
# SECURITY
# --------------------------------------------------

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# --------------------------------------------------
# EMAIL (real)
# --------------------------------------------------
# All values come from environment variables set in the Render dashboard —
# never commit real credentials here. See EMAIL_SETUP.md for where to get
# these from your transactional email provider.

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
# Emails are sent while the booking request waits, so never let a slow
# provider hang a client's booking.
EMAIL_TIMEOUT = 10

# Shown to clients as the sender. Must be on a domain you've verified with
# your email provider (see EMAIL_SETUP.md).
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", "Caldwell Cosmetics <info@caldwellcosmetics.co.uk>"
)
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# --------------------------------------------------
# STATIC
# --------------------------------------------------

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# --------------------------------------------------
# CONTENT SECURITY POLICY (django-csp)
# --------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    'whitenoise.middleware.WhiteNoiseMiddleware',
    "csp.middleware.CSPMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "axes.middleware.AxesMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "script-src": [
            "'self'",
            "'unsafe-inline'",          # inline <script> blocks throughout templates
            "https://kit.fontawesome.com",
            "https://cdn.lightwidget.com",
            "https://fonts.googleapis.com",
        ],
        "style-src": [
            "'self'",
            "'unsafe-inline'",          # inline style= attributes throughout templates
            "https://fonts.googleapis.com",
        ],
        "font-src": [
            "'self'",
            "https://fonts.gstatic.com",
            "https://ka-f.fontawesome.com",
        ],
        "img-src": [
            "'self'",
            "data:",                    # base64 signature/canvas images
            "https://res.cloudinary.com",
            "https://cdn.lightwidget.com",
            "https://www.instagram.com",
            "https://scontent.cdninstagram.com",
        ],
        "frame-src": [
            "'self'",
            "https://cdn.lightwidget.com",
        ],
        "connect-src": [
            "'self'",
            "https://ka-f.fontawesome.com",
        ],
        "media-src": [
            "'self'",
            "https://res.cloudinary.com",
        ],
    }
}

