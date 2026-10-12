"""
Shared workflow for every form (see LifecycleMixin):

    client section  →  practitioner section  →  complete (read-only)
                                             ↘  withdraw  (read-only)

Each person only ever saves their own section, and every save is logged in
FormRevision, so nothing on a form is ever overwritten without a record.
"""

import base64
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import models, transaction
from django.shortcuts import redirect
from django.utils import timezone

from .models import FormRevision

Section = FormRevision.Section
Action  = FormRevision.Action

TRUTHY = {"1", "on", "yes", "true", "True"}


def is_valid_signature(sig):
    """True only if sig is a valid base64-encoded PNG data URL."""
    if not sig or not sig.startswith("data:image/png;base64,"):
        return False
    try:
        decoded = base64.b64decode(sig.split(",", 1)[1])
        return decoded[:8] == b"\x89PNG\r\n\x1a\n"
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Finding forms
# ---------------------------------------------------------------------------

def open_forms(model, user):
    return model.objects.filter(user=user, finalised=False, withdrawn=False)


def open_form(model, user):
    """The client's in-progress form of this type, if any."""
    return open_forms(model, user).order_by("-pk").first()


def latest_completed(model, user):
    return model.objects.filter(user=user, finalised=True).order_by("-finalised_at", "-pk").first()


# ---------------------------------------------------------------------------
# Reading POST data
# ---------------------------------------------------------------------------

def values_from_post(model, fields, data):
    """
    Converts submitted values for `fields` to Python values, based on each
    model field's type. Returns (values, error) — values are returned even
    when there's an error, so the form can be re-shown with what was typed.
    """
    values, errors = {}, []

    def parse(fmt, raw, parser):
        try:
            return parser(datetime.strptime(raw, fmt)) if raw else None
        except ValueError:
            return False

    for name in fields:
        field = model._meta.get_field(name)
        raw   = data.get(name)
        label = field.verbose_name

        if isinstance(field, models.BooleanField):
            values[name] = raw in TRUTHY
        elif isinstance(field, (models.DateField, models.TimeField)):
            is_time = isinstance(field, models.TimeField) and not isinstance(field, models.DateTimeField)
            value = parse("%H:%M" if is_time else "%Y-%m-%d", raw, (lambda d: d.time()) if is_time else (lambda d: d.date()))
            if value is False:
                errors.append(f"Please enter a valid {label}.")
                value = None
            elif value is None and not field.null:
                errors.append(f"Please enter {label}.")
            values[name] = value
        elif isinstance(field, models.DecimalField):
            values[name] = None
            if raw:
                try:
                    amount = Decimal(str(raw))
                    if not 0 <= amount <= 10000:
                        raise InvalidOperation
                    values[name] = amount
                except InvalidOperation:
                    errors.append(f"Please enter a valid amount for {label}.")
        else:
            value = raw or ""
            if field.choices and value not in {c[0] for c in field.choices}:
                value = ""
            values[name] = value[:field.max_length] if field.max_length else value

    return values, (errors[0] if errors else None)


# ---------------------------------------------------------------------------
# Client section
# ---------------------------------------------------------------------------

def save_client_section(request, model, target_user, values, answer_fields, client_fields, on_answers_changed=None):
    """
    Creates the client's open form, or updates it if they already have one.

    If the client changes their answers after the practitioner has signed,
    the practitioner's signature is withdrawn — it covered the old answers.
    `on_answers_changed(form)` lets a form withdraw other signatures too
    (e.g. the Botox prescriber's).
    """
    with transaction.atomic():
        form = (
            open_forms(model, target_user)
            .select_for_update()
            .order_by("-pk")
            .first()
        )
        if form is None:
            form = model.objects.create(user=target_user, **values)
            form.log_revision(request.user, Section.CLIENT, Action.SUBMITTED, client_fields)
            return form

        before = form.snapshot(answer_fields)
        for name, value in values.items():
            setattr(form, name, value)
        form.save(update_fields=list(values))
        form.log_revision(request.user, Section.CLIENT, Action.UPDATED, client_fields)

        if form.snapshot(answer_fields) != before:
            if form.operator_signed:
                withdraw_signature(request.user, form, Section.OPERATOR)
            if on_answers_changed:
                on_answers_changed(form)
        return form


def withdraw_signature(user, form, section):
    prefix = "operator" if section == Section.OPERATOR else section
    setattr(form, f"{prefix}_signature", "")
    setattr(form, f"{prefix}_signed", False)
    setattr(form, f"{prefix}_signed_at", None)
    update = [f"{prefix}_signature", f"{prefix}_signed", f"{prefix}_signed_at"]
    if section == Section.OPERATOR:
        form.operator_signed_by = None
        update.append("operator_signed_by")
    form.save(update_fields=update)
    fields = form.OPERATOR_FIELDS if section == Section.OPERATOR else form.PRESCRIBER_FIELDS
    form.log_revision(user, section, Action.SIGNATURE_WITHDRAWN, fields)


def last_revision_was_withdrawn(form, section):
    last = form.revisions.filter(section=section).last()
    return bool(last and last.action == Action.SIGNATURE_WITHDRAWN)


# ---------------------------------------------------------------------------
# Practitioner section, completion and withdrawal
# ---------------------------------------------------------------------------

def handle_practitioner_post(request, model, pk, apply_section, section_fields=None, after_complete=None):
    """
    Handles every button on a practitioner page:

    - "save" / "sign": `apply_section(form, data)` sets the practitioner's
      fields (returning an error message or None); the section is saved,
      with the operator signature when signing (or cleared when only saving
      progress, so a signature always matches what's on the form).
    - "complete": locks the form as a read-only record.
    - "withdraw": closes it without completing, with a reason.

    Returns (response, error). A response means redirect; otherwise re-show
    the page with `error`.
    """
    data   = request.POST
    action = data.get("action")
    section_fields = section_fields or model.OPERATOR_FIELDS

    with transaction.atomic():
        form = model.objects.select_for_update().get(pk=pk)
        if form.is_closed:
            return redirect(form.view_url), None

        if action == "complete":
            if not data.get("confirm_complete"):
                return None, "Please tick the box to confirm the form is complete."
            if not form.can_finalise:
                return None, "This form can't be completed yet — check every section has been signed."
            form.finalised    = True
            form.finalised_at = timezone.now()
            form.finalised_by = request.user
            form.save(update_fields=form.FINALISE_FIELDS)
            form.log_revision(request.user, Section.FORM, Action.COMPLETED, form.all_fields)
            return redirect(form.view_url), None

        if action == "withdraw":
            reason = data.get("withdrawn_reason", "").strip()
            if not reason:
                return None, "Please give a reason for withdrawing this form."
            if not data.get("confirm_withdraw"):
                return None, "Please tick the box to confirm you want to withdraw this form."
            form.withdrawn        = True
            form.withdrawn_at     = timezone.now()
            form.withdrawn_by     = request.user
            form.withdrawn_reason = reason[:300]
            form.save(update_fields=form.WITHDRAW_FIELDS)
            form.log_revision(request.user, Section.FORM, Action.WITHDRAWN, form.all_fields)
            return redirect(form.view_url), None

        signing = action == "sign"
        sig     = data.get("operator_signature", "")
        error   = apply_section(form, data)
        if not error and signing and not is_valid_signature(sig):
            error = "A valid practitioner signature is required."
        if error:
            return None, error

        form.operator_signature = sig if signing else ""
        form.operator_signed    = signing
        form.operator_signed_at = timezone.now() if signing else None
        form.operator_signed_by = request.user if signing else None
        form.save(update_fields=list(section_fields))
        form.log_revision(request.user, Section.OPERATOR, Action.SIGNED if signing else Action.SAVED, section_fields)
        return redirect(form.operator_url), None


def practitioner_input_fields(model):
    """The practitioner's section, minus the signature (handled separately)."""
    return [n for n in model.OPERATOR_FIELDS if n not in model.OPERATOR_SIGNATURE_FIELDS]


def apply_values(model, fields):
    """An `apply_section` that parses `fields` from POST and sets them on the form."""
    def apply(form, data):
        values, error = values_from_post(model, fields, data)
        if error:
            return error
        for name, value in values.items():
            setattr(form, name, value)
        return None
    return apply
