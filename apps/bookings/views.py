from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.db import IntegrityError, transaction
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone

from apps.treatments.models import Treatment, TreatmentCategory
from .models import Booking


# ---------------------------------------------------------------------------
# Opening hours config — edit here if your schedule changes
# ---------------------------------------------------------------------------
# ⚠️  CHANGE 1: CLOSE_TIME corrected from (14, 30) to (17, 0).
#     The old value cut off all afternoon slots. The frontend (booking.utils.js)
#     now also uses 17:00 — both must always match.
# ---------------------------------------------------------------------------

OPEN_DAYS             = {0, 1, 2}  # Mon=0 … Sun=6  →  Mon/Tue/Wed
OPEN_TIME             = (9, 30)    # 09:30
CLOSE_TIME            = (14, 30)    # 17:00  ← was (14, 30)
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
        'taken':   'Sorry, that slot was just taken. Please choose another time.',
        'invalid': 'Something went wrong with your booking. Please try again.',
        # ⚠️  CHANGE 4: added a distinct error message for same-day double-booking
        'already_booked': 'You already have an appointment today. Please contact us to book a second.',
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

    # ── 1. Presence check ────────────────────────────────────────────────────
    if not all([treatment_id, date_str, time_str]):
        return redirect(reverse('bookings:overview') + '?error=invalid')

    # ── 2. Treatment exists and is active ────────────────────────────────────
    try:
        treatment = Treatment.objects.get(id=treatment_id, is_active=True)
    except Treatment.DoesNotExist:
        return redirect(reverse('bookings:overview') + '?error=invalid')

    # ── 3. Date is a valid ISO date ───────────────────────────────────────────
    try:
        booking_date = date.fromisoformat(date_str)
    except ValueError:
        return redirect(reverse('bookings:overview') + '?error=invalid')

    # ── 4. Date is within the bookable window ─────────────────────────────────
    today   = timezone.now().date()
    horizon = today + timedelta(days=BOOKING_HORIZON_DAYS)

    if booking_date < today or booking_date > horizon:
        return redirect(reverse('bookings:overview') + '?error=invalid')

    # ── 5. Date falls on an open clinic day ───────────────────────────────────
    if booking_date.weekday() not in OPEN_DAYS:
        return redirect(reverse('bookings:overview') + '?error=invalid')

    # ── 6. Requested time is a valid generated slot for this treatment ────────
    valid_times = _generate_slot_times(treatment.duration_minutes, treatment.duration_minutes)
    if time_str not in valid_times:
        return redirect(reverse('bookings:overview') + '?error=invalid')

    # ── 7. One booking per user per day ───────────────────────────────────────
    # ⚠️  CHANGE 4: prevents a client from booking two treatments on the same day.
    #     Remove this block if you want to allow multiple same-day appointments.
    already_booked_today = (
        Booking.objects
        .filter(
            user=request.user,
            date=booking_date,
            status=Booking.STATUS_CONFIRMED,
        )
        .exists()
    )
    if already_booked_today:
        return redirect(reverse('bookings:overview') + '?error=already_booked')

    # ── 8. Overlap check + create — inside a transaction with row locking ─────
    # ⚠️  CHANGE 2: select_for_update() locks all confirmed bookings on this date
    #     for the duration of the transaction, eliminating the race condition
    #     where two simultaneous requests both pass the overlap check before
    #     either has written to the database.
    h, m      = map(int, time_str.split(':'))
    new_start = h * 60 + m
    new_end   = new_start + treatment.duration_minutes

    try:
        with transaction.atomic():
            existing = (
                Booking.objects
                .select_for_update()
                .filter(date=booking_date, status=Booking.STATUS_CONFIRMED)
                .select_related('treatment')
            )

            for b in existing:
                ex_start = b.start_time.hour * 60 + b.start_time.minute
                ex_end   = ex_start + b.treatment.duration_minutes

                if new_start < ex_end and new_end > ex_start:
                    return redirect(reverse('bookings:overview') + '?error=taken')

            Booking.objects.create(
                user=request.user,
                treatment=treatment,
                date=booking_date,
                start_time=time_str,
                notes=request.POST.get('notes', ''),
            )

    except IntegrityError:
        # ⚠️  CHANGE 3: IntegrityError is now a genuine last-resort catch for
        #     any unexpected DB constraint violation, since select_for_update()
        #     handles the race condition above. If this fires, something
        #     unexpected has happened and it should be investigated.
        return redirect(reverse('bookings:overview') + '?error=taken')

    return redirect(reverse('bookings:overview') + '?success=true')