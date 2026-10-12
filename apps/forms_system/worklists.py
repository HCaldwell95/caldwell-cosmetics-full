"""
"Awaiting your signature" lists for staff.

Each returns forms (annotated with `next_appt_date` / `next_appt_time`, the
client's next confirmed booking) plus:

    worklist_status  new | draft | changed | ready
    worklist_url     where the staff member acts on it

`split_by_appointment` separates clients with an upcoming appointment
(soonest first) from those with nothing booked.
"""

from django.db.models import OuterRef, Prefetch, Subquery
from django.urls import reverse
from django.utils import timezone

from apps.bookings.models import Booking

from .models import (
    BotoxConsentForm, ConsultationForm, FormRevision, LaserReConsent,
    PhotographyConsent, PRPConsentForm, RecordCard,
)

LIFECYCLE_MODELS = (ConsultationForm, PhotographyConsent, BotoxConsentForm, PRPConsentForm, LaserReConsent, RecordCard)


def _open_forms(model):
    today = timezone.now().date()
    next_booking = (
        Booking.objects
        .filter(user=OuterRef("user"), status=Booking.STATUS_CONFIRMED, date__gte=today)
        .order_by("date", "start_time")
    )
    return (
        model.objects
        .filter(finalised=False, withdrawn=False, user__is_active=True)
        .select_related("user")
        .annotate(
            next_appt_date=Subquery(next_booking.values("date")[:1]),
            next_appt_time=Subquery(next_booking.values("start_time")[:1]),
        )
    )


def _with_revisions(qs, section):
    return qs.prefetch_related(Prefetch(
        "revisions",
        queryset=FormRevision.objects.filter(section=section),
        to_attr="section_revisions",
    ))


def _status_from_revisions(form):
    last = form.section_revisions[-1] if form.section_revisions else None
    if last and last.action == FormRevision.Action.SIGNATURE_WITHDRAWN:
        return "changed"
    return "draft" if last else "new"


def split_by_appointment(forms):
    """(with an upcoming appointment, soonest first; with none, oldest first)."""
    booked   = sorted((f for f in forms if f.next_appt_date),
                      key=lambda f: (f.next_appt_date, f.next_appt_time or 0, f.started_at))
    unbooked = sorted((f for f in forms if not f.next_appt_date), key=lambda f: f.started_at)
    return booked, unbooked


def prescriber_worklist():
    """Botox forms the client has signed that still need a prescriber's signature."""
    forms = list(_with_revisions(
        _open_forms(BotoxConsentForm).filter(client_signed=True, prescriber_signed=False),
        FormRevision.Section.PRESCRIBER,
    ))
    for f in forms:
        f.worklist_status = _status_from_revisions(f)
        f.worklist_url    = reverse("forms_system:botox_prescriber", args=[f.pk])
    return forms


def practitioner_worklist():
    """
    Every open form waiting on the practitioner: the client has done their
    part and it needs the practitioner's signature — or it's signed and just
    needs completing. Forms only waiting on someone else (e.g. a Botox form
    the practitioner has signed but the prescriber hasn't) are left out.
    """
    forms = []
    for model in LIFECYCLE_MODELS:
        for f in _with_revisions(_open_forms(model), FormRevision.Section.OPERATOR):
            if not f.client_section_done and model is not RecordCard:
                continue
            if f.can_finalise:
                f.worklist_status = "ready"
            elif f.operator_signed:
                continue  # signed — waiting on someone else
            else:
                f.worklist_status = _status_from_revisions(f)
            f.worklist_url = f.operator_url
            forms.append(f)
    return forms
