import os
import dj_database_url
from pathlib import Path
from dotenv import load_dotenv

import cloudinary
import cloudinary.uploader
import cloudinary.api


load_dotenv()
# --------------------------------------------------
# BASE DIR
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# --------------------------------------------------
# CLOUDINARY CONFIG
# --------------------------------------------------

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

# --------------------------------------------------
# SECURITY
# --------------------------------------------------
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "unsafe-dev-secret-key")

# --------------------------------------------------
# APPLICATIONS
# --------------------------------------------------

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

LOCAL_APPS = [
    "apps.core.apps.CoreConfig",
    "apps.treatments.apps.TreatmentsConfig",
    "apps.bookings.apps.BookingsConfig",
    "apps.accounts.apps.AccountsConfig",
    'apps.dashboard.apps.DashboardConfig',
    'apps.forms_system.apps.FormsSystemConfig',
]

THIRD_PARTY_APPS = [
    # e.g. "crispy_forms",
    'cloudinary',
    'cloudinary_storage',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# --------------------------------------------------
# MIDDLEWARE
# --------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    'whitenoise.middleware.WhiteNoiseMiddleware',
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# --------------------------------------------------
# URLS / WSGI / ASGI
# --------------------------------------------------

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --------------------------------------------------
# TEMPLATES
# --------------------------------------------------

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
            ],
        },
    },
]

# --------------------------------------------------
# DATABASE
# --------------------------------------------------

DATABASES = {
    "default": dj_database_url.config(
        default="sqlite:///db.sqlite3",
        conn_max_age=600,
    )
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': os.getenv('DB_NAME'),
#         'USER': os.getenv('DB_USER'),
#         'PASSWORD': os.getenv('DB_PASSWORD'),
#         'HOST': os.getenv('DB_HOST'),
#         'PORT': os.getenv('DB_PORT'),
#     }
# }

# --------------------------------------------------
# AUTH
# --------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

AUTH_USER_MODEL = "accounts.User"

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True

# --------------------------------------------------
# STATIC & MEDIA
# --------------------------------------------------

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = str(BASE_DIR / "staticfiles")

STATICFILES_STORAGE = 'whitenoise.storage.StaticFilesStorage'

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# --------------------------------------------------
# DEFAULTS
# --------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------
# AUTH REDIRECTS & BACKEND
# --------------------------------------------------
LOGIN_URL           = "/accounts/login/"
LOGIN_REDIRECT_URL  = "/accounts/profile/"
LOGOUT_REDIRECT_URL = "/"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]