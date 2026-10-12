"""
Access control for staff pages.

- Practitioner (superuser): everything.
- Prescriber (User.role): clients and their forms, plus the prescriber
  section of the Botox form. No calendar, bookings, bundles or credit.
"""

from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import never_cache


def is_practitioner(user):
    return user.is_authenticated and user.is_practitioner


def is_prescriber(user):
    return user.is_authenticated and user.is_prescriber


def is_clinical_staff(user):
    return user.is_authenticated and user.is_clinical_staff


def _staff_view(test):
    def decorator(view_func):
        return never_cache(login_required(
            user_passes_test(test, login_url="accounts:login")(view_func)
        ))
    return decorator


practitioner_required   = _staff_view(is_practitioner)
prescriber_required     = _staff_view(is_prescriber)
clinical_staff_required = _staff_view(is_clinical_staff)
