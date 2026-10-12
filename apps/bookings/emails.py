"""
Client-facing booking emails.

Called from apps.dashboard.signals.on_booking_saved whenever a Booking is
created, cancelled, or amended — from the website or the practitioner
dashboard. Sending failures are logged but never raise, so a slow or
down email provider can never break a booking.
"""

import functools
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.dateparse import parse_date, parse_time
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def _context_for(booking):
    # Bookings created via Booking.objects.create(date="...", start_time="...")
    # still hold the raw strings when post_save fires, so coerce them first.
    date = booking.date
    if isinstance(date, str):
        date = parse_date(date)
    start_time = booking.start_time
    if isinstance(start_time, str):
        start_time = parse_time(start_time)

    return {
        "client_name": booking.user.full_name,
        "treatment_name": getattr(booking.treatment, "name", "your treatment"),
        "date": date.strftime("%A %d %B %Y"),
        "time": start_time.strftime("%H:%M"),
    }


def _never_raise(func):
    # Never let an email problem (bad data, template error, provider outage)
    # take down a booking.
    @functools.wraps(func)
    def wrapper(booking):
        try:
            func(booking)
        except Exception:
            logger.exception("Failed to send %s email for booking %s", func.__name__, booking.pk)
    return wrapper


def _send(booking, subject, template_name, context):
    to_email = booking.user.email
    if not to_email:
        return

    html_body = render_to_string(template_name, context)
    text_body = strip_tags(html_body)

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=False)


@_never_raise
def send_booking_confirmation(booking):
    context = _context_for(booking)
    _send(
        booking,
        subject=f"Booking confirmed — {context['treatment_name']}",
        template_name="emails/booking_confirmed.html",
        context=context,
    )


@_never_raise
def send_booking_cancelled(booking):
    context = _context_for(booking)
    _send(
        booking,
        subject=f"Your appointment on {context['date']} has been cancelled",
        template_name="emails/booking_cancelled.html",
        context=context,
    )


@_never_raise
def send_booking_amended(booking):
    context = _context_for(booking)
    _send(
        booking,
        subject=f"Your booking has been updated — {context['treatment_name']}",
        template_name="emails/booking_amended.html",
        context=context,
    )
