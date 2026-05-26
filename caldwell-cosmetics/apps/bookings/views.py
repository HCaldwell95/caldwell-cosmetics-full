from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.db import IntegrityError
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone

from apps.treatments.models import Treatment, TreatmentCategory
from .models import Booking


# ---------------------------------------------------------------------------
# Opening hours config — edit here if your schedule changes
# ---------------------------------------------------------------------------

OPEN_DAYS             = {1, 2, 3}  # Mon=0 … Sun=6  →  Mon/Tue/Wed
OPEN_TIME             = (9, 30)    # 09:30
CLOSE_TIME            = (14, 30)   # 14:30
SLOT_INTERVAL_MINUTES = 30         # Cadence between slot start times
BOOKING_HORIZON_DAYS  = 60         # How many days ahead to expose


def _build_booked_set():
    """
    Returns a set of (date_str, start_minutes, end_minutes) for every
    confirmed booking within the horizon. Treatment-agnostic — one booking
    blocks that time window for all treatments.
    """
    today   = timezone.now().date()
    horizon = today + timedelta(days=BOOKING_HORIZON_DAYS)

    bookings = (
        Booking.objects
        .filter(
            status=Booking.STATUS_CONFIRMED,
            date__gte=today,
            date__lte=horizon,
        )
        .select_related('treatment')
        .values('date', 'start_time', 'treatment__duration_minutes')
    )

    blocked = set()

    for b in bookings:
        date_str      = b['date'].strftime('%Y-%m-%d')
        start_minutes = b['start_time'].hour * 60 + b['start_time'].minute
        duration      = b['treatment__duration_minutes']
        end_minutes   = start_minutes + duration

        blocked.add((date_str, start_minutes, end_minutes))

    return blocked


def _generate_slot_times(duration_minutes, interval_minutes=SLOT_INTERVAL_MINUTES):
    """
    Return a list of 'HH:MM' strings representing every possible slot
    start time for a treatment of the given duration, within opening hours.
    """
    slots  = []
    h, m   = OPEN_TIME
    ch, cm = CLOSE_TIME

    while True:
        end_h = h + (m + duration_minutes) // 60
        end_m = (m + duration_minutes) % 60

        if (end_h, end_m) > (ch, cm):
            break

        slots.append(f"{h:02d}:{m:02d}")

        m += interval_minutes
        if m >= 60:
            h += 1
            m -= 60

    return slots


def _build_slots_json(treatments, booked_set):
    """
    For each treatment, generate all possible slot start times and mark
    any that overlap with an existing booking as booked — regardless of
    which treatment that booking was made for.
    """
    today   = timezone.now().date()
    horizon = today + timedelta(days=BOOKING_HORIZON_DAYS)
    data    = {}

    for treatment in treatments:
        t_key  = str(treatment.id)
        times  = _generate_slot_times(treatment.duration_minutes, treatment.duration_minutes)
        data[t_key] = {}

        current = today
        while current <= horizon:
            if current.weekday() in OPEN_DAYS:
                date_str     = current.strftime('%Y-%m-%d')
                booked_times = []

                for t in times:
                    h, m       = map(int, t.split(':'))
                    slot_start = h * 60 + m
                    slot_end   = slot_start + treatment.duration_minutes

                    overlaps = any(
                        slot_start < b_end and slot_end > b_start
                        for (d, b_start, b_end) in booked_set
                        if d == date_str
                    )

                    if overlaps:
                        booked_times.append(t)

                data[t_key][date_str] = {
                    'times':  times,
                    'booked': booked_times,
                }

            current += timedelta(days=1)

    return data


@never_cache
@login_required
def overview(request):
    treatments = (
        Treatment.objects
        .select_related('category')
        .filter(is_active=True)
    )

    categories = (
        TreatmentCategory.objects
        .filter(is_active=True)
        .prefetch_related('treatments')
    )

    booked_set = _build_booked_set()
    slots_json = _build_slots_json(treatments, booked_set)

    error_map = {
        'taken':   'Sorry, that slot was just booked by someone else. Please choose another time.',
        'invalid': 'Something went wrong with your booking. Please try again.',
    }

    context = {
        'categories':        categories,
        'treatments':        treatments,
        'booked_slots_json': slots_json,
        'show_success':      request.GET.get('success') == 'true',
        'error_message':     error_map.get(request.GET.get('error', ''), ''),
    }

    return render(request, 'bookings/overview.html', context)


@never_cache
@login_required
def create_booking(request):
    if request.method != 'POST':
        return redirect('bookings:overview')

    treatment_id = request.POST.get('treatment_id')
    date_str     = request.POST.get('date')
    time_str     = request.POST.get('start_time')

    if not all([treatment_id, date_str, time_str]):
        return redirect(reverse('bookings:overview') + '?error=invalid')

    try:
        treatment = Treatment.objects.get(id=treatment_id, is_active=True)
    except Treatment.DoesNotExist:
        return redirect(reverse('bookings:overview') + '?error=invalid')

    try:
        booking_date = date.fromisoformat(date_str)
    except ValueError:
        return redirect(reverse('bookings:overview') + '?error=invalid')

    today   = timezone.now().date()
    horizon = today + timedelta(days=BOOKING_HORIZON_DAYS)

    if booking_date < today or booking_date > horizon:
        return redirect(reverse('bookings:overview') + '?error=invalid')

    if booking_date.weekday() not in OPEN_DAYS:
        return redirect(reverse('bookings:overview') + '?error=invalid')

    valid_times = _generate_slot_times(treatment.duration_minutes, treatment.duration_minutes)
    if time_str not in valid_times:
        return redirect(reverse('bookings:overview') + '?error=invalid')

    # Check for overlaps with any existing booking on this date,
    # across all treatments — one booking blocks that window for everyone
    h, m      = map(int, time_str.split(':'))
    new_start = h * 60 + m
    new_end   = new_start + treatment.duration_minutes

    existing = (
        Booking.objects
        .filter(date=booking_date, status=Booking.STATUS_CONFIRMED)
        .select_related('treatment')
    )

    for b in existing:
        ex_start = b.start_time.hour * 60 + b.start_time.minute
        ex_end   = ex_start + b.treatment.duration_minutes

        if new_start < ex_end and new_end > ex_start:
            return redirect(reverse('bookings:overview') + '?error=taken')

    try:
        Booking.objects.create(
            user=request.user,
            treatment=treatment,
            date=booking_date,
            start_time=time_str,
            notes=request.POST.get('notes', ''),
        )
    except IntegrityError:
        return redirect(reverse('bookings:overview') + '?error=taken')

    return redirect(reverse('bookings:overview') + '?success=true')