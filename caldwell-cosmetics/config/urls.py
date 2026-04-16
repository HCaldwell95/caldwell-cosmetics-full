from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    # Public-facing pages
    path("", include("apps.core.urls")),  # root points to pages app

    # Other apps
    path("treatments/", include("apps.treatments.urls")),
    path("bookings/", include("apps.bookings.urls")),
    path("accounts/", include("apps.accounts.urls")),
]
