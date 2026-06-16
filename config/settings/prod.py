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

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

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
    }
}

