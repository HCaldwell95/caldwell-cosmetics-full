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

    # Operator step 2
    path("botox/<int:pk>/operator/",   views.botox_operator,       name="botox_operator"),
    path("prp/<int:pk>/operator/",     views.prp_operator,         name="prp_operator"),

    # Record cards (practitioner only)
    path("records/<int:user_id>/new/", views.record_card_new,      name="record_card_new"),
    path("records/<int:pk>/view/",     views.record_card_view,     name="record_card_view"),

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