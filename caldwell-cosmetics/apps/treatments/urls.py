
from django.urls import path
from . import views

app_name = "treatments"

urlpatterns = [
    path("", views.treatments, name="treatments"),
    path("<slug:slug>/", views.treatment_detail, name="treatment_detail"),
]