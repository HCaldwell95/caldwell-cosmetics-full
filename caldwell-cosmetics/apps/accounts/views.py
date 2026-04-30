from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.shortcuts import get_object_or_404, redirect, render

from .forms import LoginForm, ProfileEditForm, RegistrationForm
from .models import Profile


# --------------------------------------------------
# REGISTRATION
# --------------------------------------------------

def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:profile")

    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, f"Welcome, {user.first_name}! Your account has been created.")
        return redirect("accounts:profile")

    return render(request, "accounts/register.html", {"form": form})


# --------------------------------------------------
# LOGIN / LOGOUT
# --------------------------------------------------

class LoginView(DjangoLoginView):
    form_class = LoginForm
    template_name = "accounts/login.html"

    def get_success_url(self):
        return self.get_redirect_url() or "/accounts/profile/"

    def form_valid(self, form):
        messages.success(self.request, f"Welcome back, {form.get_user().first_name}!")
        return super().form_valid(form)


def logout_view(request):
    if request.method == "POST":
        logout(request)
        messages.info(request, "You have been logged out.")
    return redirect("core:home")


# --------------------------------------------------
# CLIENT PROFILE
# --------------------------------------------------

@login_required
def profile(request):
    profile = get_object_or_404(Profile, user=request.user)
    return render(request, "accounts/profile.html", {"profile": profile})


@login_required
def profile_edit(request):
    profile = get_object_or_404(Profile, user=request.user)
    form = ProfileEditForm(
        request.POST or None,
        request.FILES or None,
        instance=profile,
        user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("accounts:profile")

    return render(request, "accounts/profile_edit.html", {"form": form, "profile": profile})