from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.utils import timezone

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

@login_required
def deactivate_account(request):
    if request.method == "POST":
        user = request.user
        profile = user.profile
        profile.deactivated_at = timezone.now()
        profile.save(update_fields=["deactivated_at"])
        user.is_active = False
        user.save(update_fields=["is_active"])
        logout(request)
        messages.info(request, "Your account has been deactivated. We're sorry to see you go.")
        return redirect("core:home")
    return render(request, "accounts/deactivate_account.html")


@login_required
def profile_bookings(request):
    from apps.bookings.models import Booking
 
    today = timezone.now().date()
 
    qs = (
        Booking.objects
        .filter(user=request.user)
        .select_related('treatment__category')
        .order_by('date', 'start_time')
    )
 
    upcoming = []
    past     = []
 
    for b in qs:
        entry = {
            'id':               b.pk,
            'treatment':        b.treatment.name,
            'category_colour':  b.treatment.category.colour,
            'date':             b.date.strftime('%A %d %B %Y'),
            'start_time':       b.start_time.strftime('%H:%M'),
            'duration':         b.treatment.duration_minutes,
            'status':           b.status,
        }
        if b.date >= today and b.status == Booking.STATUS_CONFIRMED:
            upcoming.append(entry)
        else:
            past.append(entry)
 
    # Most recent past first
    past.reverse()
 
    return JsonResponse({'upcoming': upcoming, 'past': past})