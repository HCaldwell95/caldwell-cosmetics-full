from django.urls import path
from . import views

app_name = "forms_system"

urlpatterns = [
    # Client-facing consent forms
    path("consultation/",                          views.consultation_form,   name="consultation"),
    path("consultation/<int:user_id>/view/",       views.consultation_view,   name="consultation_view"),
    path("consultation/<int:user_id>/new/",        views.consultation_new,    name="consultation_new"),
    path("photography/",               views.photography_consent,  name="photography"),
    path("botox/",                     views.botox_client,         name="botox_client"),
    path("prp/",                       views.prp_client,           name="prp_client"),
    path("laser/reconsent/",           views.laser_reconsent,      name="laser_reconsent"),

    # Practitioner sections (save / sign, then complete or withdraw)
    path("consultation/<int:pk>/operator/", views.consultation_operator, name="consultation_operator"),
    path("photography/<int:pk>/operator/",  views.photography_operator,  name="photography_operator"),
    path("botox/<int:pk>/operator/",   views.botox_operator,       name="botox_operator"),
    path("botox/<int:pk>/prescriber/", views.botox_prescriber,     name="botox_prescriber"),
    path("botox/<int:pk>/client/",     views.botox_client_edit,    name="botox_client_edit"),
    path("prp/<int:pk>/operator/",     views.prp_operator,         name="prp_operator"),
    path("laser/<int:pk>/operator/",   views.laser_operator,       name="laser_operator"),

    # Read-only records, with their full history
    path("photography/<int:pk>/view/", views.photography_view,     name="photography_view"),
    path("botox/<int:pk>/view/",       views.botox_view,           name="botox_view"),
    path("prp/<int:pk>/view/",         views.prp_view,             name="prp_view"),
    path("laser/<int:pk>/view/",       views.laser_reconsent_view, name="laser_reconsent_view"),

    # Record cards (practitioner only)
    path("records/<int:user_id>/new/", views.record_card_new,      name="record_card_new"),
    path("records/<int:pk>/edit/",     views.record_card_edit,     name="record_card_edit"),
    path("records/<int:pk>/view/",     views.record_card_view,     name="record_card_view"),

    # Botox treatment cards (practitioner only; the prescriber can view them)
    path("botox-cards/<int:user_id>/new/", views.botox_card_new,  name="botox_card_new"),
    path("botox-cards/<int:pk>/edit/",     views.botox_card_edit, name="botox_card_edit"),
    path("botox-cards/<int:pk>/view/",     views.botox_card_view, name="botox_card_view"),

    # Pre / post treatment information pages
    path("botox/pre-treatment/",       views.botox_pre_treatment,  name="botox_pre_treatment"),
    path("botox/post-treatment/",      views.botox_post_treatment, name="botox_post_treatment"),
    path("prp/pre-treatment/",         views.prp_pre_treatment,    name="prp_pre_treatment"),
    path("prp/post-treatment/",        views.prp_post_treatment,   name="prp_post_treatment"),
    path("laser/pre-treatment/",       views.laser_pre_treatment,  name="laser_pre_treatment"),
    path("laser/post-treatment/",      views.laser_post_treatment, name="laser_post_treatment"),

    # AJAX status endpoint (used by profile page and dashboard)
    path("status/<int:user_id>/",      views.form_status,          name="form_status"),
]