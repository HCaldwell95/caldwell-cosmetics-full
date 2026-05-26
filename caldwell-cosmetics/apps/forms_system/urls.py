from django.urls import path
from . import views

app_name = "forms_system"

urlpatterns = [
    # Client-facing
    path("consultation/",              views.consultation_form,    name="consultation"),
    path("photography/",               views.photography_consent,  name="photography"),
    path("botox/",                     views.botox_client,         name="botox_client"),

    # Operator step 2 for botox (practitioner only)
    path("botox/<int:pk>/operator/",   views.botox_operator,       name="botox_operator"),

    # Record cards (practitioner only)
    path("records/<int:user_id>/new/", views.record_card_new,      name="record_card_new"),
    path("records/<int:pk>/view/",     views.record_card_view,     name="record_card_view"),

    # AJAX status endpoint (used by profile page and dashboard)
    path("status/<int:user_id>/",      views.form_status,          name="form_status"),
]