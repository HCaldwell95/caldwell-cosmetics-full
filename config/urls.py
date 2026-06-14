from django.contrib import admin
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView

from apps.core.sitemaps import sitemaps

urlpatterns = [
    path("admin/", admin.site.urls),

    # SEO
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),

    # Public-facing pages
    path("", include("apps.core.urls")),

    # Other apps
    path("treatments/", include("apps.treatments.urls")),
    path("bookings/", include("apps.bookings.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("forms/", include("apps.forms_system.urls")),
]
