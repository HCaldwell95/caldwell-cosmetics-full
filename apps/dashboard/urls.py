from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("",                                views.dashboard,        name="dashboard"),
    path("bookings/data/",                  views.bookings_data,    name="bookings_data"),
    path("bookings/create/",                views.booking_create,   name="booking_create"),
    path("bookings/<int:pk>/edit/",         views.booking_edit,     name="booking_edit"),
    path("bookings/<int:pk>/cancel/",       views.booking_cancel,   name="booking_cancel"),
    path("users/search/",                   views.user_search,      name="user_search"),

    # Profile section
    path("clients/",                        views.client_list,      name="client_list"),
    path("clients/<int:pk>/",               views.client_profile,   name="client_profile"),
    path("clients/<int:pk>/edit/",          views.client_edit,      name="client_edit"),

    # Bundle management
    path("clients/<int:pk>/bundles/add/",           views.bundle_add,           name="bundle_add"),
    path("clients/<int:pk>/bundles/<int:bundle_pk>/use/", views.bundle_use_session,  name="bundle_use_session"),

    # Credit management
    path("clients/<int:pk>/credit/adjust/", views.credit_adjust,    name="credit_adjust"),
]