from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("",                                views.dashboard,        name="dashboard"),
    path("clients-page/",                   views.clients_page,     name="clients_page"),
    path("bookings/data/",                  views.bookings_data,    name="bookings_data"),
    path("bookings/create/",                views.booking_create,   name="booking_create"),
    path("bookings/<int:pk>/edit/",         views.booking_edit,     name="booking_edit"),
    path("bookings/<int:pk>/cancel/",       views.booking_cancel,   name="booking_cancel"),
    path("users/search/",                   views.user_search,      name="user_search"),

    # Closed dates (holidays)
    path("closed-dates/",                   views.closed_dates_page,  name="closed_dates_page"),
    path("closed-dates/data/",              views.closed_dates_data,  name="closed_dates_data"),
    path("closed-dates/create/",            views.closed_date_create, name="closed_date_create"),
    path("closed-dates/<int:pk>/delete/",   views.closed_date_delete, name="closed_date_delete"),

    # Profile section
    path("clients/",                        views.client_list,      name="client_list"),
    path("clients/create/",                 views.client_create,    name="client_create"),
    path("clients/<int:pk>/",               views.client_profile,   name="client_profile"),
    path("clients/<int:pk>/edit/",          views.client_edit,      name="client_edit"),

    # Bundle management
    path("clients/<int:pk>/bundles/add/",           views.bundle_add,           name="bundle_add"),
    path("clients/<int:pk>/bundles/<int:bundle_pk>/use/", views.bundle_use_session,  name="bundle_use_session"),

    # Credit management
    path("clients/<int:pk>/credit/adjust/", views.credit_adjust,    name="credit_adjust"),

    # Client notes (operator only)
    path("clients/<int:pk>/notes/new/",              views.note_new,  name="note_new"),
    path("clients/<int:pk>/notes/<int:note_pk>/",    views.note_view, name="note_view"),

    # Notifications
    path("notifications/",                          views.notifications_page,        name="notifications_page"),
    path("notifications/data/",                     views.notifications_data,        name="notifications_data"),
    path("notifications/count/",                    views.notification_count,        name="notification_count"),
    path("notifications/mark-all/",                 views.notification_mark_all_read, name="notification_mark_all"),
    path("notifications/<int:pk>/mark-read/",       views.notification_mark_read,    name="notification_mark_read"),
]