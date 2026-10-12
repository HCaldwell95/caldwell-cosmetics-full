from datetime import datetime

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.accounts.permissions import clinical_staff_required, practitioner_required
from . import lifecycle
from .lifecycle import Action, Section
from .models import (
    ConsultationForm, BotoxConsentForm, PhotographyConsent,
    RecordCard, PRPConsentForm, LaserReConsent,
)

User = get_user_model()


staff_required = practitioner_required


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _dob_is_minor(dob_str):
    from datetime import date as date_type
    try:
        dob = date_type.fromisoformat(str(dob_str))
        today = date_type.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return age < 18
    except (ValueError, TypeError, AttributeError):
        return False


def _profile_is_minor(user):
    try:
        dob = user.profile.date_of_birth
        return _dob_is_minor(dob.isoformat()) if dob else False
    except Exception:
        return False


GUARDIAN_FIELDS = ["guardian_name", "guardian_relationship", "guardian_phone", "guardian_email"]

_validate_sig = lifecycle.is_valid_signature


def _guardian_error(data, is_minor):
    if not is_minor:
        return None
    if not (data.get("guardian_name") and data.get("guardian_phone") and _validate_sig(data.get("guardian_signature", ""))):
        return "Clients under 18 need a parent or guardian's name, phone number and signature."
    return None


def _post_submit_redirect(request):
    """Staff go back to the dashboard; clients go to their profile."""
    if request.user.is_staff:
        return redirect("dashboard:dashboard")
    return redirect("accounts:profile")


def _is_practitioner_mode(request):
    return request.user.is_superuser and request.GET.get("on_behalf_of") is not None


def _get_target_user(request):
    """
    Returns the user the form is being completed for.
    For clients this is request.user.
    For practitioners completing on behalf, it's the user_id param.
    """
    if _is_practitioner_mode(request):
        uid = request.GET.get("on_behalf_of") or request.POST.get("on_behalf_of")
        return get_object_or_404(User, pk=uid)
    return request.user


def _is_xhr(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


# ---------------------------------------------------------------------------
# Form status endpoint (AJAX — used by profile page and dashboard)
# ---------------------------------------------------------------------------

def _latest(model, user):
    """The client's most recent form of this type that hasn't been withdrawn."""
    return model.objects.filter(user=user, withdrawn=False).order_by("-pk").first()


def _status(form):
    if form is None:
        return {"completed": False, "client_signed": False, "fully_complete": False, "date": None, "id": None}
    return {
        "completed":       form.client_section_done,   # client has done their part
        "client_signed":   form.client_section_done,
        "fully_complete":  form.finalised,
        "date":            form.completed_at.strftime("%d %b %Y"),
        "by_practitioner": getattr(form, "completed_by_practitioner", False),
        "id":              form.pk,
    }


@login_required
def form_status(request, user_id):
    """
    Returns JSON describing which forms the user has completed.
    Accessible by the user themselves or clinical staff.
    """
    if request.user.pk != user_id and not request.user.is_clinical_staff:
        return JsonResponse({"error": "Forbidden"}, status=403)

    user = get_object_or_404(User, pk=user_id)

    laser_forms   = LaserReConsent.objects.filter(user=user, withdrawn=False)
    laser_latest  = laser_forms.order_by("-completed_at").first()
    record_cards  = RecordCard.objects.filter(user=user, withdrawn=False)
    record_latest = record_cards.order_by("-date").first()

    return JsonResponse({
        "consultation": _status(_latest(ConsultationForm, user)),
        "photography":  _status(_latest(PhotographyConsent, user)),
        "botox":        _status(_latest(BotoxConsentForm, user)),
        "prp":          _status(_latest(PRPConsentForm, user)),
        "laser_reconsent": {
            "count":     laser_forms.count(),
            "last_date": laser_latest.completed_at.strftime("%d %b %Y") if laser_latest else None,
        },
        "record_cards": {
            "count":     record_cards.count(),
            "latest_id": record_latest.pk if record_latest else None,
            "last_date": record_latest.date.strftime("%d %b %Y") if record_latest else None,
        },
    })


# ---------------------------------------------------------------------------
# Shared view builders
#
# Every form follows the same lifecycle (see lifecycle.py):
#   client page        — the client (or practitioner on their behalf) fills in
#                        and updates their section of their in-progress form
#   practitioner page  — the practitioner saves / signs their section, then
#                        completes or withdraws the form
#   record page        — read-only view of the form and its full history
# ---------------------------------------------------------------------------

def _client_page(request, model, template, *, signature_field="signature",
                 prefill_from_last=False, on_answers_changed=None, context=None):
    """
    Shows / saves the client's section of their in-progress form of `model`,
    starting a new one if they don't have one.

    Template context:
      f              — values to show (in-progress form, entered values after
                       an error, or the last completed form if prefill_from_last)
      editing        — True if updating an in-progress form
      current        — the in-progress form, if any
      last_completed — their most recent completed form of this type
    """
    target_user = _get_target_user(request)
    on_behalf   = _is_practitioner_mode(request)
    current     = lifecycle.open_form(model, target_user)
    error       = None
    shown       = current

    if request.method == "POST":
        data     = request.POST
        sig      = data.get(signature_field, "")
        is_minor = _dob_is_minor(data.get("date_of_birth", "")) if hasattr(model, "date_of_birth") \
            else _profile_is_minor(target_user)

        answers, error = lifecycle.values_from_post(model, model.CLIENT_ANSWER_FIELDS, data)
        if not is_minor:
            answers.update({name: "" for name in GUARDIAN_FIELDS if name in answers})

        if not _validate_sig(sig):
            error = "Your signature didn't come through. Please sign in the box again and resubmit."
        error = error or _guardian_error(data, is_minor)

        if error:
            if _is_xhr(request):
                return JsonResponse({"ok": False, "error": error}, status=400)
            # Re-show the form with what they entered, rather than a bare error.
            shown = model(user=target_user, **answers)
        else:
            values = dict(answers)
            values[signature_field]      = sig
            values["guardian_signature"] = data.get("guardian_signature", "") if is_minor else ""
            if hasattr(model, "client_signed"):
                values["client_signed"] = True
            if hasattr(model, "client_signed_at"):
                values["client_signed_at"] = timezone.now()
            if on_behalf:
                values["practitioner"] = request.user
                if hasattr(model, "completed_by_practitioner"):
                    values["completed_by_practitioner"] = True

            form = lifecycle.save_client_section(
                request, model, target_user, values,
                model.CLIENT_ANSWER_FIELDS, model.CLIENT_FIELDS, on_answers_changed,
            )

            if _is_xhr(request):
                return JsonResponse({"ok": True, "id": form.pk})
            if on_behalf:
                # Straight on to the practitioner's section.
                return redirect(form.operator_url)
            messages.success(request, f"Your {model.FORM_TITLE} has been saved.")
            return _post_submit_redirect(request)

    last_completed = lifecycle.latest_completed(model, target_user)
    if shown is None and prefill_from_last:
        shown = last_completed

    return render(request, template, {
        "f":                shown,
        "editing":          current is not None,
        "current":          current,
        "last_completed":   last_completed,
        "error":            error,
        "form_title":       model.FORM_TITLE,
        "target_user":      target_user,
        "on_behalf":        on_behalf,
        "profile_is_minor": _profile_is_minor(target_user),
        **(context or {}),
    }, status=400 if error else 200)


def _practitioner_page(request, model, pk, template, *, apply_section=None, section_fields=None, context=None, as_name=None):
    """
    The practitioner's page for one form: their section (save / sign) plus
    Complete and Withdraw. Closed forms redirect to the read-only record.
    """
    form = get_object_or_404(model, pk=pk)
    if form.is_closed:
        return redirect(form.view_url)

    error = None
    if request.method == "POST":
        apply_section = apply_section or lifecycle.apply_values(model, lifecycle.practitioner_input_fields(model))
        response, error = lifecycle.handle_practitioner_post(request, model, pk, apply_section, section_fields)
        if response:
            return response
        form.refresh_from_db()

    return render(request, template, {
        "f":     form,
        **({as_name: form} if as_name else {}),
        "error": error,
        "signature_withdrawn": lifecycle.last_revision_was_withdrawn(form, Section.OPERATOR),
        **(context or {}),
    })


def _record_page(request, model, pk, template, context=None, as_name=None):
    form = get_object_or_404(model, pk=pk)
    return render(request, template, {
        "f":         form,
        **({as_name: form} if as_name else {}),
        "revisions": form.revisions.select_related("user"),
        **(context or {}),
    })


# ---------------------------------------------------------------------------
# Laser Consultation
# ---------------------------------------------------------------------------

@login_required
def consultation_form(request):
    # A new consultation starts from the client's last one, as most details
    # carry over — consents and the signature must be given afresh.
    return _client_page(request, ConsultationForm, "forms_system/consultation/form.html", prefill_from_last=True, context={
        "form_treatment_choices": ConsultationForm.TREATMENT_CHOICES,
    })


@staff_required
def consultation_operator(request, pk):
    return _practitioner_page(request, ConsultationForm, pk, "forms_system/consultation/operator.html")


@clinical_staff_required
def consultation_view(request, user_id):
    """Read-only view of a consultation; ?form_pk=<pk> selects a specific historical entry."""
    target_user = get_object_or_404(User, pk=user_id)
    all_forms   = list(ConsultationForm.objects.filter(user=target_user).order_by("-completed_at"))

    form_pk = request.GET.get("form_pk")
    form = next((f for f in all_forms if str(f.pk) == str(form_pk)), None) if form_pk else None
    form = form or (all_forms[0] if all_forms else None)

    return render(request, "forms_system/consultation/view.html", {
        "target_user": target_user,
        "form":        form,
        "f":           form,
        "all_forms":   all_forms,
        "revisions":   form.revisions.select_related("user") if form else [],
    })


@staff_required
def consultation_new(request, user_id):
    """Start (or continue) a consultation on the client's behalf."""
    return redirect(f"{reverse('forms_system:consultation')}?on_behalf_of={user_id}")


# ---------------------------------------------------------------------------
# Photography Consent
# ---------------------------------------------------------------------------

@login_required
def photography_consent(request):
    # With a consent on file and nothing in progress, show it — with the
    # option to complete an updated consent (?new=1).
    target_user = _get_target_user(request)
    on_file     = lifecycle.latest_completed(PhotographyConsent, target_user)
    in_progress = lifecycle.open_form(PhotographyConsent, target_user)
    show_on_file = on_file and not in_progress and request.method == "GET" and not request.GET.get("new")

    return _client_page(request, PhotographyConsent, "forms_system/photography/consent.html", prefill_from_last=True, context={
        "existing": on_file if show_on_file else None,
    })


@staff_required
def photography_operator(request, pk):
    return _practitioner_page(request, PhotographyConsent, pk, "forms_system/photography/operator.html")


@clinical_staff_required
def photography_view(request, pk):
    return _record_page(request, PhotographyConsent, pk, "forms_system/photography/view.html")


# ---------------------------------------------------------------------------
# Botox Consent & Prescription
#
# Like every form, plus a prescriber section between the client's and the
# practitioner's. If the client changes their answers after the prescriber
# has signed, the prescriber's signature is withdrawn.
# ---------------------------------------------------------------------------

def _withdraw_prescriber_signature(request):
    def withdraw(form):
        if form.prescriber_signed:
            lifecycle.withdraw_signature(request.user, form, Section.PRESCRIBER)
    return withdraw


@login_required
def botox_client(request):
    return _client_page(request, BotoxConsentForm, "forms_system/botox/client.html",
                        on_answers_changed=_withdraw_prescriber_signature(request))


def _prescriber_block_reason(user, botox):
    """Why `user` can't edit the prescriber section, or None if they can."""
    if botox.is_closed:
        return "This form has been closed (completed or withdrawn) and is now read-only."
    if not user.is_prescriber:
        return "Only a prescriber can complete this section."
    if not hasattr(user, "prescriber_details"):
        return "Your prescriber registration details haven't been set up yet. Please ask the clinic to add them."
    if not botox.client_signed:
        return "The client hasn't completed their section of this form yet."
    return None


def _prescriber_values(botox):
    return {
        "prescriber_face_to_face":  botox.prescriber_face_to_face,
        "prescription_decision":    botox.prescription_decision,
        "prescribed_product":       botox.prescribed_product,
        "prescribed_dose":          botox.prescribed_dose,
        "prescription_valid_until": botox.prescription_valid_until.isoformat() if botox.prescription_valid_until else "",
        "prescriber_notes":         botox.prescriber_notes,
    }


@clinical_staff_required
def botox_prescriber(request, pk):
    """
    Prescriber reviews the client's section and records their decision.
    They can save progress or sign, and keep editing until the practitioner
    completes the form. The practitioner can view this page but not sign it.
    """
    botox = get_object_or_404(BotoxConsentForm, pk=pk)
    if botox.is_closed:
        return redirect("forms_system:botox_view", pk=pk)

    error  = None
    values = _prescriber_values(botox)

    if request.method == "POST":
        data    = request.POST
        values  = data
        signing = data.get("action") == "sign"

        with transaction.atomic():
            botox = BotoxConsentForm.objects.select_for_update().get(pk=pk)
            error = _prescriber_block_reason(request.user, botox)

            decision = data.get("prescription_decision", "")
            if decision not in BotoxConsentForm.PrescriptionDecision.values:
                decision = ""
            product     = data.get("prescribed_product", "").strip()
            dose        = data.get("prescribed_dose", "").strip()
            sig         = data.get("prescriber_signature", "")
            valid_until = None

            if not error and data.get("prescription_valid_until"):
                try:
                    valid_until = datetime.strptime(data["prescription_valid_until"], "%Y-%m-%d").date()
                except ValueError:
                    error = "Please enter a valid 'valid until' date."

            if not error and signing:
                if not data.get("prescriber_face_to_face"):
                    error = "Please confirm you have assessed the client face to face."
                elif not decision:
                    error = "Please choose whether you are prescribing."
                elif decision == BotoxConsentForm.PrescriptionDecision.PRESCRIBED and not (product and dose):
                    error = "Please enter the product and dose being prescribed."
                elif not _validate_sig(sig):
                    error = "A valid prescriber signature is required."

            if not error:
                details = request.user.prescriber_details
                botox.prescriber               = request.user
                botox.prescriber_name          = details.display_name
                botox.prescriber_registration  = details.registration_display
                botox.prescriber_face_to_face  = bool(data.get("prescriber_face_to_face"))
                botox.prescription_decision    = decision
                botox.prescribed_product       = product
                botox.prescribed_dose          = dose
                botox.prescription_valid_until = valid_until
                botox.prescriber_notes         = data.get("prescriber_notes", "")
                # Saving progress after signing withdraws the signature — it
                # must always match what's on the form.
                botox.prescriber_signature     = sig if signing else ""
                botox.prescriber_signed        = signing
                botox.prescriber_signed_at     = timezone.now() if signing else None
                botox.save(update_fields=BotoxConsentForm.PRESCRIBER_FIELDS)
                botox.log_revision(
                    request.user, Section.PRESCRIBER,
                    Action.SIGNED if signing else Action.SAVED,
                    BotoxConsentForm.PRESCRIBER_FIELDS,
                )
                if signing:
                    # Back to the worklist so they can move on to the next client.
                    messages.success(request, f"Signed for {botox.user.full_name}.")
                    return redirect("dashboard:prescriber_home")
                messages.success(request, "Progress saved — not yet signed.")
                return redirect("forms_system:botox_prescriber", pk=pk)

    block_reason = _prescriber_block_reason(request.user, botox)

    return render(request, "forms_system/botox/prescriber.html", {
        "botox":     botox,
        "can_edit":  block_reason is None,
        "block_reason": block_reason if request.user.is_prescriber else None,
        "signature_withdrawn": lifecycle.last_revision_was_withdrawn(botox, Section.PRESCRIBER),
        "error":     error,
        "values":    values,
        "decisions": BotoxConsentForm.PrescriptionDecision.choices,
        "prescriber_details": getattr(request.user, "prescriber_details", None),
    })


@staff_required
def botox_operator(request, pk):
    return _practitioner_page(request, BotoxConsentForm, pk, "forms_system/botox/operator.html", as_name="botox")


@clinical_staff_required
def botox_view(request, pk):
    return _record_page(request, BotoxConsentForm, pk, "forms_system/botox/view.html", as_name="botox")


# ---------------------------------------------------------------------------
# PRP Consent
# ---------------------------------------------------------------------------

@login_required
def prp_client(request):
    return _client_page(request, PRPConsentForm, "forms_system/prp/client.html")


@staff_required
def prp_operator(request, pk):
    return _practitioner_page(request, PRPConsentForm, pk, "forms_system/prp/operator.html", as_name="prp")


@clinical_staff_required
def prp_view(request, pk):
    return _record_page(request, PRPConsentForm, pk, "forms_system/prp/view.html")


# ---------------------------------------------------------------------------
# Laser Re-Consent
# ---------------------------------------------------------------------------

@login_required
def laser_reconsent(request):
    return _client_page(request, LaserReConsent, "forms_system/laser/reconsent.html", signature_field="client_signature")


@staff_required
def laser_operator(request, pk):
    return _practitioner_page(request, LaserReConsent, pk, "forms_system/laser/operator.html")


@clinical_staff_required
def laser_reconsent_view(request, pk):
    return _record_page(request, LaserReConsent, pk, "forms_system/laser/reconsent_view.html", as_name="reconsent")


# ---------------------------------------------------------------------------
# Record Cards
#
# Practitioner-led: the practitioner fills in the card, taking the client's
# re-consent signature on their device. It stays an editable draft until
# they sign and complete it.
# ---------------------------------------------------------------------------

def _apply_record_card(card, data):
    """Sets the card's fields from POST; signatures are only replaced when re-drawn."""
    fields = [n for n in RecordCard.editable_fields()
              if n not in ("reconsent_signature", "reconsent_signed_at", "guardian_signature")]
    values, error = lifecycle.values_from_post(RecordCard, fields, data)
    if error:
        return error
    for name, value in values.items():
        setattr(card, name, value)

    reconsent = data.get("reconsent_signature", "")
    if reconsent and _validate_sig(reconsent):
        card.reconsent_signature = reconsent
        card.reconsent_signed_at = timezone.now()
    guardian = data.get("guardian_signature", "")
    if guardian and _validate_sig(guardian):
        card.guardian_signature = guardian
    return None


def _record_card_section_fields():
    return RecordCard.editable_fields() + RecordCard.OPERATOR_SIGNATURE_FIELDS


def _previous_card(user, exclude_pk=None):
    cards = RecordCard.objects.filter(user=user, withdrawn=False).order_by("-treatment_number")
    if exclude_pk:
        cards = cards.exclude(pk=exclude_pk)
    return cards.first()


@staff_required
def record_card_new(request, user_id):
    target_user = get_object_or_404(User, pk=user_id)
    error = None

    if request.method == "POST":
        card  = RecordCard(user=target_user, created_by=request.user)
        error = _apply_record_card(card, request.POST)
        if not error:
            card.save()
            card.log_revision(request.user, Section.OPERATOR, Action.SAVED, _record_card_section_fields())
            # Signing / completing happens on the card's own page.
            if request.POST.get("action") in ("sign", "complete"):
                return record_card_edit(request, card.pk)
            return redirect(card.operator_url)

    return render(request, "forms_system/record_card/new.html", {
        "target_user": target_user,
        "previous":    _previous_card(target_user),
        "is_minor":    _profile_is_minor(target_user),
        "f":           None,
        "error":       error,
    })


@staff_required
def record_card_edit(request, pk):
    card = get_object_or_404(RecordCard, pk=pk)
    return _practitioner_page(
        request, RecordCard, pk, "forms_system/record_card/new.html",
        apply_section=_apply_record_card,
        section_fields=_record_card_section_fields(),
        context={
            "target_user": card.user,
            "previous":    _previous_card(card.user, exclude_pk=card.pk),
            "is_minor":    _profile_is_minor(card.user),
        },
    )


@login_required
def record_card_view(request, pk):
    card = get_object_or_404(RecordCard, pk=pk)

    # Clients can only see their own; clinical staff can see all
    if not request.user.is_clinical_staff and card.user != request.user:
        return _post_submit_redirect(request)

    return _record_page(request, RecordCard, pk, "forms_system/record_card/view.html", context={"card": card})


# ---------------------------------------------------------------------------
# Informational pages (pre / post treatment)
# ---------------------------------------------------------------------------

@login_required
def botox_pre_treatment(request):
    return render(request, "forms_system/botox/pre_treatment.html")


@login_required
def botox_post_treatment(request):
    return render(request, "forms_system/botox/post_treatment.html")


@login_required
def prp_pre_treatment(request):
    return render(request, "forms_system/prp/pre_treatment.html")


@login_required
def prp_post_treatment(request):
    return render(request, "forms_system/prp/post_treatment.html")


@login_required
def laser_pre_treatment(request):
    return render(request, "forms_system/laser/pre_treatment.html")


@login_required
def laser_post_treatment(request):
    return render(request, "forms_system/laser/post_treatment.html")