from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),        # Home page
    path("privacy/", views.privacy, name="privacy"),
    path("terms/", views.terms, name="terms"),
    path("cookies/", views.cookies, name="cookies"),
]
