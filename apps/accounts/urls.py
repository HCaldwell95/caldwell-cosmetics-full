from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("register/",     views.register,            name="register"),
    path("login/",        views.LoginView.as_view(),  name="login"),
    path("logout/",       views.logout_view,          name="logout"),
    path("profile/",      views.profile,              name="profile"),
    path("profile/edit/", views.profile_edit,         name="profile_edit"),
    path('bookings/',          views.profile_bookings,    name='profile_bookings'),
    path('credit-history/',   views.credit_history,       name='credit_history'),
    path('deactivate/',        views.deactivate_account,  name='deactivate_account'),
]