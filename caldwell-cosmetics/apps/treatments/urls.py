from django.urls import path
from . import views

app_name = "treatments"

urlpatterns = [
    path("", views.list, name="list"),
]
