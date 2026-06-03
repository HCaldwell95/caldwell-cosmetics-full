from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),        # Home page
    path("privacy/", views.privacy, name="privacy"),
    path("terms/", views.terms, name="terms"),
    path("cookies/", views.cookies, name="cookies"),
    path("myjourney/", views.myjourney, name="myjourney"),
    path("skin-journey/", views.skin_journey, name="skin_journey"),
    path("phformula/", views.phformula, name="phformula"),
    path("lynton/", views.lynton, name="lynton"),
]
