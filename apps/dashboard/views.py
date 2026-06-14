import json
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from apps.bookings.models import Booking
from apps.bookings.views import (
    OPEN_DAYS,
    OPEN_TIME,
    CLOSE_TIME,
    BOOKING_HORIZON_DAYS,
    _generate_slot_times,
)
from apps.treatments.models import Treatment, TreatmentCategory
from apps.forms_system.models import (
    ConsultationForm,
    BotoxConsentForm,
    PhotographyConsent,
    RecordCard,
    PRPConsentForm,
    LaserReConsent,
)

try:
    from apps.accounts.models import User, PrepaidBundle, AccountCredit, CreditTransaction
except ImportError:
    from django.contrib.auth import get_user_model
    User = get_user_model()


def is_admin(user):
    return user.is_authenticated and user.is_superuser


admin_required = user_passes_test(is_admin, login_url="accounts:login")


def admin_view(view_func):
    return never_cache(login_required(admin_required(view_func)))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_latest_form(model, user):
    try:
        return model.objects.filter(user=user).latest("completed_at")
    except model.DoesNotExist:
        return None


def _client_form_status(user):
    """Returns a dict summarising form completion for a client."""
    consultation = _get_latest_form(ConsultationForm, user)
    photography  = _get_latest_form(PhotographyConsent, user)
    botox        = _get_latest_form(BotoxConsentForm, user)
    prp          = _get_latest_form(PRPConsentForm, user)
    record_count = RecordCard.objects.filter(user=user).count()

    try:
        laser_latest = LaserReConsent.objects.filter(user=user).latest("completed_at")
        laser_count  = LaserReConsent.objects.filter(user=user).count()
    except Exception:
        laser_latest = None
        laser_count  = 0

    return {
        "consultation": {
            "completed":        consultation is not None,
            "date":             consultation.completed_at if consultation else None,
            "by_practitioner":  consultation.completed_by_practitioner if consultation else False,
        },
        "photography": {
            "completed":        photography is not None,
            "date":             photography.completed_at if photography else None,
            "by_practitioner":  photography.completed_by_practitioner if photography else False,
        },
        "botox": {
            "client_signed":    botox.client_signed if botox else False,
            "fully_complete":   botox.is_fully_complete if botox else False,
            "date":             botox.completed_at if botox else None,
            "id":               botox.pk if botox else None,
        },
        "prp": {
            "client_signed":    prp.client_signed if prp else False,
            "fully_complete":   prp.is_fully_complete if prp else False,
            "date":             prp.completed_at if prp else None,
            "id":               prp.pk if prp else None,
        },
        "laser_reconsent": {
            "count":            laser_count,
            "last_date":        laser_latest.completed_at.strftime("%d %b %Y") if laser_latest else None,
        },
        "record_cards": record_count,
    }


def _client_bundle_data(user):
    try:
        bundles = PrepaidBundle.objects.filter(user=user).order_by("-date_purchased")
    except Exception:
        bundles = []
    return bundles


def _client_credit(user):
    try:
        credit, _ = AccountCredit.objects.get_or_create(user=user)
        return credit
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main dashboard view
# ---------------------------------------------------------------------------

@admin_view
def dashboard(request):
    treatments = Treatment.objects.filter(is_active=True).select_related("category")
    categories = TreatmentCategory.objects.filter(is_active=True)

    context = {
        "treatments": treatments,
        "categories": categories,
    }
    return render(request, "core/dashboard.html", context)


# ---------------------------------------------------------------------------
# Calendar data endpoint
# ---------------------------------------------------------------------------

@admin_view
def bookings_data(request):
    start_str = request.GET.get("start")
    end_str   = request.GET.get("end")

    try:
        start_date = date.fromisoformat(start_str)
        end_date   = date.fromisoformat(end_str)
    except (TypeError, ValueError):
        today      = timezone.now().date()
        start_date = today.replace(day=1)
        end_date   = start_date + timedelta(days=60)

    bookings = (
        Booking.objects
        .filter(date__gte=start_date, date__lte=end_date)
        .select_related("treatment", "treatment__category", "user", "user__profile")
        .order_by("date", "start_time")
    )

    events = []
    for b in bookings:
        start_minutes = b.start_time.hour * 60 + b.start_time.minute
        end_minutes   = start_minutes + b.treatment.duration_minutes
        end_h, end_m  = divmod(end_minutes, 60)

        events.append({
            "id":           b.pk,
            "treatment":    b.treatment.name,
            "client":       b.user.full_name,
            "client_id":    b.user.pk,
            "email":        b.user.email,
            "phone":        getattr(b.user.profile, "phone_number", ""),
            "date":         b.date.strftime("%Y-%m-%d"),
            "start_time":   b.start_time.strftime("%H:%M"),
            "end_time":     f"{end_h:02d}:{end_m:02d}",
            "duration":     b.treatment.duration_minutes,
            "price":        str(b.treatment.price),
            "notes":        b.notes,
            "status":       b.status,
            "category_colour": b.treatment.category.colour,
        })

    return JsonResponse({"events": events})


# ---------------------------------------------------------------------------
# Booking create / edit / cancel
# ---------------------------------------------------------------------------

@admin_view
@require_POST
def booking_create(request):
    data = json.loads(request.body)

    user_id      = data.get("user_id")
    treatment_id = data.get("treatment_id")
    date_str     = data.get("date")
    time_str     = data.get("start_time")
    notes        = data.get("notes", "")

    errors = {}
    if not user_id:      errors["user"]       = "Please select a client."
    if not treatment_id: errors["treatment"]   = "Please select a treatment."
    if not date_str:     errors["date"]        = "Please select a date."
    if not time_str:     errors["start_time"]  = "Please select a time."
    if errors:
        return JsonResponse({"ok": False, "errors": errors}, status=400)

    try:
        user         = User.objects.get(pk=user_id)
        treatment    = Treatment.objects.get(pk=treatment_id, is_active=True)
        booking_date = date.fromisoformat(date_str)
    except (User.DoesNotExist, Treatment.DoesNotExist, ValueError) as e:
        return JsonResponse({"ok": False, "errors": {"__all__": str(e)}}, status=400)

    if booking_date.weekday() not in OPEN_DAYS:
        return JsonResponse(
            {"ok": False, "errors": {"date": "The clinic is closed on this day."}},
            status=400,
        )

    valid_times = _generate_slot_times(treatment.duration_minutes, treatment.duration_minutes)
    if time_str not in valid_times:
        return JsonResponse(
            {"ok": False, "errors": {"start_time": "Invalid time slot for this treatment."}},
            status=400,
        )

    h, m      = map(int, time_str.split(":"))
    new_start = h * 60 + m
    new_end   = new_start + treatment.duration_minutes

    overlapping = (
        Booking.objects
        .filter(date=booking_date, status=Booking.STATUS_CONFIRMED)
        .select_related("treatment")
    )
    for b in overlapping:
        ex_start = b.start_time.hour * 60 + b.start_time.minute
        ex_end   = ex_start + b.treatment.duration_minutes
        if new_start < ex_end and new_end > ex_start:
            return JsonResponse(
                {"ok": False, "errors": {"start_time": "This time overlaps with an existing booking."}},
                status=400,
            )

    booking = Booking.objects.create(
        user=user,
        treatment=treatment,
        date=booking_date,
        start_time=time_str,
        notes=notes,
        status=Booking.STATUS_CONFIRMED,
    )

    return JsonResponse({"ok": True, "id": booking.pk})


@admin_view
@require_POST
def booking_edit(request, pk):
    booking      = get_object_or_404(Booking, pk=pk)
    data         = json.loads(request.body)
    treatment_id = data.get("treatment_id")
    date_str     = data.get("date")
    time_str     = data.get("start_time")
    notes        = data.get("notes", "")
    status       = data.get("status", booking.status)

    errors = {}
    try:
        treatment    = Treatment.objects.get(pk=treatment_id, is_active=True)
        booking_date = date.fromisoformat(date_str)
    except (Treatment.DoesNotExist, ValueError) as e:
        return JsonResponse({"ok": False, "errors": {"__all__": str(e)}}, status=400)

    if booking_date.weekday() not in OPEN_DAYS:
        errors["date"] = "The clinic is closed on this day."

    valid_times = _generate_slot_times(treatment.duration_minutes, treatment.duration_minutes)
    if time_str not in valid_times:
        errors["start_time"] = "Invalid time slot for this treatment."

    if errors:
        return JsonResponse({"ok": False, "errors": errors}, status=400)

    h, m      = map(int, time_str.split(":"))
    new_start = h * 60 + m
    new_end   = new_start + treatment.duration_minutes

    for b in Booking.objects.filter(date=booking_date, status=Booking.STATUS_CONFIRMED).exclude(pk=pk).select_related("treatment"):
        ex_start = b.start_time.hour * 60 + b.start_time.minute
        ex_end   = ex_start + b.treatment.duration_minutes
        if new_start < ex_end and new_end > ex_start:
            return JsonResponse(
                {"ok": False, "errors": {"start_time": "This time overlaps with an existing booking."}},
                status=400,
            )

    booking.treatment  = treatment
    booking.date       = booking_date
    booking.start_time = time_str
    booking.notes      = notes
    booking.status     = status
    booking.save()

    return JsonResponse({"ok": True})


@admin_view
@require_POST
def booking_cancel(request, pk):
    booking        = get_object_or_404(Booking, pk=pk)
    booking.status = Booking.STATUS_CANCELLED
    booking.save()

    # Uncomment once email is configured:
    # send_mail(
    #     subject="Your appointment has been cancelled",
    #     message=(
    #         f"Hi {booking.user.full_name},\n\n"
    #         f"Your {booking.treatment.name} appointment on "
    #         f"{booking.date.strftime('%A %d %B %Y')} at "
    #         f"{booking.start_time.strftime('%H:%M')} has been cancelled.\n\n"
    #         f"Please contact us to rebook.\n\nCaldwell Cosmetics"
    #     ),
    #     from_email=settings.DEFAULT_FROM_EMAIL,
    #     recipient_list=[booking.user.email],
    # )

    return JsonResponse({"ok": True})


# ---------------------------------------------------------------------------
# User search (for booking modal)
# ---------------------------------------------------------------------------

@admin_view
def user_search(request):
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"users": []})

    users = (
        User.objects
        .filter(is_active=True)
        .filter(
            models.Q(first_name__icontains=q) |
            models.Q(last_name__icontains=q)  |
            models.Q(email__icontains=q)
        )
        .select_related("profile")
        [:10]
    )

    return JsonResponse({
        "users": [
            {
                "id":    u.pk,
                "name":  u.full_name,
                "email": u.email,
                "phone": getattr(u, "profile", None) and u.profile.phone_number or "",
            }
            for u in users
        ]
    })


# ---------------------------------------------------------------------------
# Client list
# ---------------------------------------------------------------------------

@admin_view
def client_list(request):
    q = request.GET.get("q", "").strip()

    clients = User.objects.filter(is_active=True, is_staff=False, is_superuser=False)

    if q:
        clients = clients.filter(
            models.Q(first_name__icontains=q) |
            models.Q(last_name__icontains=q)  |
            models.Q(email__icontains=q)
        )

    clients = clients.select_related("profile").order_by("last_name", "first_name")

    return JsonResponse({
        "clients": [
            {
                "id":    c.pk,
                "name":  c.full_name,
                "email": c.email,
                "phone": getattr(c, "profile", None) and c.profile.phone_number or "",
                "joined": c.date_joined.strftime("%d %b %Y"),
            }
            for c in clients
        ]
    })


# ---------------------------------------------------------------------------
# Client profile detail
# ---------------------------------------------------------------------------

@admin_view
def client_profile(request, pk):
    user    = get_object_or_404(User, pk=pk)
    profile = getattr(user, "profile", None)

    today = timezone.now().date()

    upcoming = (
        Booking.objects
        .filter(user=user, status=Booking.STATUS_CONFIRMED, date__gte=today)
        .select_related("treatment")
        .order_by("date", "start_time")
    )

    past = (
        Booking.objects
        .filter(user=user, date__lt=today)
        .select_related("treatment")
        .order_by("-date", "-start_time")[:10]
    )

    bundles = _client_bundle_data(user)
    credit  = _client_credit(user)
    forms   = _client_form_status(user)

    treatments = Treatment.objects.filter(is_active=True).order_by("name")

    record_cards = (
        RecordCard.objects
        .filter(user=user)
        .order_by("-treatment_number")
    )

    return JsonResponse({
        "user": {
            "id":           user.pk,
            "name":         user.full_name,
            "email":        user.email,
            "joined":       user.date_joined.strftime("%d %b %Y"),
            "phone":        profile.phone_number if profile else "",
            "dob":          profile.date_of_birth.strftime("%d %b %Y") if profile and profile.date_of_birth else "",
            "skin_type":     profile.get_skin_type_display() if profile else "",
            "skin_type_key": profile.skin_type if profile else "",
            "address":      "\n".join(filter(None, [
                profile.address_line_1 if profile else "",
                profile.address_line_2 if profile else "",
                profile.town_city      if profile else "",
                profile.postcode       if profile else "",
            ])) if profile else "",
            "medical_notes": profile.medical_notes if profile else "",
            "gdpr_consent":  profile.gdpr_consent if profile else False,
        },
        "upcoming_bookings": [
            {
                "id":        b.pk,
                "treatment": b.treatment.name,
                "date":      b.date.strftime("%A %d %B %Y"),
                "time":      b.start_time.strftime("%H:%M"),
                "duration":  b.treatment.duration_minutes,
                "status":    b.status,
            }
            for b in upcoming
        ],
        "past_bookings": [
            {
                "id":        b.pk,
                "treatment": b.treatment.name,
                "date":      b.date.strftime("%A %d %B %Y"),
                "time":      b.start_time.strftime("%H:%M"),
                "status":    b.status,
            }
            for b in past
        ],
        "bundles": [
            {
                "id":               b.pk,
                "treatment_name":   b.treatment_name,
                "total_sessions":   b.total_sessions,
                "sessions_used":    b.sessions_used,
                "sessions_remaining": b.sessions_remaining,
                "status":           b.status,
                "date_purchased":   b.date_purchased.strftime("%d %b %Y"),
                "expiry_date":      b.expiry_date.strftime("%d %b %Y") if b.expiry_date else None,
                "notes":            b.notes,
            }
            for b in bundles
        ],
        "credit": {
            "balance": str(credit.balance) if credit else "0.00",
        },
        "forms": forms,
        "record_cards": [
            {
                "id":               rc.pk,
                "treatment_number": rc.treatment_number,
                "date":             rc.date.strftime("%d %b %Y"),
                "treatment_for":    rc.treatment_for,
            }
            for rc in record_cards
        ],
        "treatments": [
            {"id": t.pk, "name": t.name}
            for t in treatments
        ],
    })


# ---------------------------------------------------------------------------
# Client profile edit
# ---------------------------------------------------------------------------

@admin_view
@require_POST
def client_edit(request, pk):
    user    = get_object_or_404(User, pk=pk)
    profile = getattr(user, "profile", None)
    data    = json.loads(request.body)

    user.first_name = data.get("first_name", user.first_name)
    user.last_name  = data.get("last_name",  user.last_name)
    if data.get("email"):
        user.email = data["email"]
    user.save()

    if profile:
        profile.phone_number   = data.get("phone_number",   profile.phone_number)
        profile.address_line_1 = data.get("address_line_1", profile.address_line_1)
        profile.address_line_2 = data.get("address_line_2", profile.address_line_2)
        profile.town_city      = data.get("town_city",      profile.town_city)
        profile.postcode       = data.get("postcode",       profile.postcode)
        profile.medical_notes  = data.get("medical_notes",  profile.medical_notes)

        dob = data.get("date_of_birth")
        if dob:
            try:
                from datetime import date as date_type
                profile.date_of_birth = date_type.fromisoformat(dob)
            except ValueError:
                pass

        profile.skin_type = data.get("skin_type", profile.skin_type)
        profile.save()

    return JsonResponse({"ok": True})


# ---------------------------------------------------------------------------
# Bundle management
# ---------------------------------------------------------------------------

@admin_view
@require_POST
def bundle_add(request, pk):
    user = get_object_or_404(User, pk=pk)
    data = json.loads(request.body)

    treatment_name = data.get("treatment_name", "").strip()
    total_sessions = data.get("total_sessions")
    notes          = data.get("notes", "")
    expiry_date    = data.get("expiry_date") or None

    if not treatment_name or not total_sessions:
        return JsonResponse(
            {"ok": False, "error": "Treatment name and session count are required."},
            status=400,
        )

    try:
        total_sessions = int(total_sessions)
    except (ValueError, TypeError):
        return JsonResponse({"ok": False, "error": "Invalid session count."}, status=400)

    bundle = PrepaidBundle.objects.create(
        user=user,
        treatment_name=treatment_name,
        total_sessions=total_sessions,
        notes=notes,
        expiry_date=expiry_date or None,
    )

    return JsonResponse({
        "ok": True,
        "bundle": {
            "id":                 bundle.pk,
            "treatment_name":     bundle.treatment_name,
            "total_sessions":     bundle.total_sessions,
            "sessions_used":      bundle.sessions_used,
            "sessions_remaining": bundle.sessions_remaining,
            "status":             bundle.status,
            "date_purchased":     bundle.date_purchased.strftime("%d %b %Y"),
            "expiry_date":        bundle.expiry_date.strftime("%d %b %Y") if bundle.expiry_date else None,
            "notes":              bundle.notes,
        }
    })


@admin_view
@require_POST
def bundle_use_session(request, pk, bundle_pk):
    get_object_or_404(User, pk=pk)
    bundle = get_object_or_404(PrepaidBundle, pk=bundle_pk)

    if bundle.is_complete:
        return JsonResponse({"ok": False, "error": "This bundle is already complete."}, status=400)

    bundle.sessions_used += 1
    if bundle.is_complete:
        bundle.status = "completed"
    bundle.save()

    return JsonResponse({
        "ok": True,
        "sessions_used":      bundle.sessions_used,
        "sessions_remaining": bundle.sessions_remaining,
        "status":             bundle.status,
    })


# ---------------------------------------------------------------------------
# Credit management
# ---------------------------------------------------------------------------

@admin_view
@require_POST
def credit_adjust(request, pk):
    user   = get_object_or_404(User, pk=pk)
    data   = json.loads(request.body)
    credit, _ = AccountCredit.objects.get_or_create(user=user)

    transaction_type = data.get("type")
    description      = data.get("description", "")

    try:
        amount = abs(float(data.get("amount", 0)))
    except (ValueError, TypeError):
        return JsonResponse({"ok": False, "error": "Invalid amount."}, status=400)

    if transaction_type not in ("credit", "deduct", "refund"):
        return JsonResponse({"ok": False, "error": "Invalid transaction type."}, status=400)

    if transaction_type in ("deduct",) and amount > float(credit.balance):
        return JsonResponse({"ok": False, "error": "Insufficient credit balance."}, status=400)

    if transaction_type == "deduct":
        credit.balance -= amount
    else:
        credit.balance += amount

    credit.save()

    CreditTransaction.objects.create(
        account=credit,
        transaction_type=transaction_type,
        amount=amount,
        description=description,
        created_by=request.user,
    )

    return JsonResponse({"ok": True, "balance": str(credit.balance)})