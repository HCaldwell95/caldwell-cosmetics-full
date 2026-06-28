from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.bookings.models import Booking
from apps.forms_system.models import (
    ConsultationForm,
    PhotographyConsent,
    BotoxConsentForm,
    PRPConsentForm,
    LaserReConsent,
)


def _notify(client, form_type, form_id):
    from apps.dashboard.models import Notification
    Notification.objects.get_or_create(
        client=client,
        form_type=form_type,
        form_id=form_id,
    )


@receiver(post_save, sender=ConsultationForm, dispatch_uid='dashboard.on_consultation_saved')
def on_consultation_saved(sender, instance, created, **kwargs):
    if created and not instance.completed_by_practitioner:
        _notify(instance.user, 'consultation', instance.pk)


@receiver(post_save, sender=PhotographyConsent, dispatch_uid='dashboard.on_photography_saved')
def on_photography_saved(sender, instance, created, **kwargs):
    if created and not instance.completed_by_practitioner:
        _notify(instance.user, 'photography', instance.pk)


@receiver(pre_save, sender=BotoxConsentForm, dispatch_uid='dashboard.before_botox_save')
def before_botox_save(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_client_signed = (
                BotoxConsentForm.objects
                .values_list('client_signed', flat=True)
                .get(pk=instance.pk)
            )
        except BotoxConsentForm.DoesNotExist:
            instance._prev_client_signed = False
    else:
        instance._prev_client_signed = False


@receiver(post_save, sender=BotoxConsentForm, dispatch_uid='dashboard.on_botox_saved')
def on_botox_saved(sender, instance, created, **kwargs):
    prev = getattr(instance, '_prev_client_signed', False)
    if instance.client_signed and not prev:
        _notify(instance.user, 'botox', instance.pk)


@receiver(pre_save, sender=PRPConsentForm, dispatch_uid='dashboard.before_prp_save')
def before_prp_save(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_client_signed = (
                PRPConsentForm.objects
                .values_list('client_signed', flat=True)
                .get(pk=instance.pk)
            )
        except PRPConsentForm.DoesNotExist:
            instance._prev_client_signed = False
    else:
        instance._prev_client_signed = False


@receiver(post_save, sender=PRPConsentForm, dispatch_uid='dashboard.on_prp_saved')
def on_prp_saved(sender, instance, created, **kwargs):
    prev = getattr(instance, '_prev_client_signed', False)
    if instance.client_signed and not prev:
        _notify(instance.user, 'prp', instance.pk)


@receiver(post_save, sender=LaserReConsent, dispatch_uid='dashboard.on_laser_reconsent_saved')
def on_laser_reconsent_saved(sender, instance, created, **kwargs):
    if created and instance.client_signature:
        _notify(instance.user, 'laser_reconsent', instance.pk)


# ---------------------------------------------------------------------------
# Booking signals
# ---------------------------------------------------------------------------

def _fmt_date(d):
    try:
        return d.strftime('%a %d %b %Y')
    except AttributeError:
        return str(d)


def _fmt_time(t):
    try:
        return t.strftime('%H:%M')
    except AttributeError:
        return str(t)[:5]


@receiver(pre_save, sender=Booking, dispatch_uid='dashboard.before_booking_save')
def before_booking_save(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = (
                Booking.objects
                .values('status', 'treatment_id', 'date', 'start_time')
                .get(pk=instance.pk)
            )
            instance._prev_status       = old['status']
            instance._prev_treatment_id = old['treatment_id']
            instance._prev_date         = old['date']
            instance._prev_start_time   = old['start_time']
        except Booking.DoesNotExist:
            instance._prev_status = None
    else:
        instance._prev_status = None


@receiver(post_save, sender=Booking, dispatch_uid='dashboard.on_booking_saved')
def on_booking_saved(sender, instance, created, **kwargs):
    from apps.dashboard.models import Notification

    name     = instance.user.full_name or instance.user.email
    date_str = _fmt_date(instance.date)
    time_str = _fmt_time(instance.start_time)

    try:
        treatment_name = instance.treatment.name
    except Exception:
        treatment_name = 'treatment'

    if created:
        Notification.objects.create(
            client=instance.user,
            form_type=Notification.BOOKING_CREATED,
            form_id=instance.pk,
            message_text=f"{name} booked {treatment_name} on {date_str} at {time_str}",
        )
        return

    prev_status = getattr(instance, '_prev_status', None)

    if prev_status == Booking.STATUS_CONFIRMED and instance.status == Booking.STATUS_CANCELLED:
        Notification.objects.create(
            client=instance.user,
            form_type=Notification.BOOKING_CANCELLED,
            form_id=instance.pk,
            message_text=f"{name}'s {treatment_name} appointment on {date_str} was cancelled",
        )
        return

    if instance.status == Booking.STATUS_CONFIRMED:
        prev_tid   = getattr(instance, '_prev_treatment_id', None)
        prev_date  = getattr(instance, '_prev_date', None)
        prev_time  = getattr(instance, '_prev_start_time', None)

        date_changed      = prev_date  is not None and prev_date  != instance.date
        time_changed      = prev_time  is not None and prev_time  != instance.start_time
        treatment_changed = prev_tid   is not None and prev_tid   != instance.treatment_id

        if date_changed or time_changed or treatment_changed:
            Notification.objects.create(
                client=instance.user,
                form_type=Notification.BOOKING_AMENDED,
                form_id=instance.pk,
                message_text=f"{name}'s booking was changed to {treatment_name} on {date_str} at {time_str}",
            )
