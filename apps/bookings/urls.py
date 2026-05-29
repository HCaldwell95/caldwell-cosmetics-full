from django.urls import path
from . import views

app_name = "bookings"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("create/", views.create_booking, name="create"),
]