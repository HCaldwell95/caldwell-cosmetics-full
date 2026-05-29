import json
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
from .utils import bool_from_post

from .models import ConsultationForm, BotoxConsentForm, PhotographyConsent, RecordCard

User = get_user_model()


def staff_required(view_func):
    """Restricts view to superusers (practitioner)."""
    from django.contrib.auth.decorators import user_passes_test
    return login_required(
        user_passes_test(
            lambda u: u.is_superuser,
            login_url="accounts:login",
        )(view_func)
    )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _get_or_none(model, **kwargs):
    try:
        return model.objects.filter(**kwargs).latest("completed_at")
    except model.DoesNotExist:
        return None


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


# ---------------------------------------------------------------------------
# Form status endpoint (AJAX — used by profile page and dashboard)
# ---------------------------------------------------------------------------

@login_required
def form_status(request, user_id):
    """
    Returns JSON describing which forms the user has completed.
    Accessible by the user themselves or any superuser.
    """
    if request.user.pk != user_id and not request.user.is_superuser:
        return JsonResponse({"error": "Forbidden"}, status=403)

    user = get_object_or_404(User, pk=user_id)

    consultation  = _get_or_none(ConsultationForm, user=user)
    photography   = _get_or_none(PhotographyConsent, user=user)
    botox         = _get_or_none(BotoxConsentForm, user=user)
    record_count  = RecordCard.objects.filter(user=user).count()

    return JsonResponse({
        "consultation": {
            "completed": consultation is not None,
            "date": consultation.completed_at.strftime("%d %b %Y") if consultation else None,
            "by_practitioner": consultation.completed_by_practitioner if consultation else False,
        },
        "photography": {
            "completed": photography is not None,
            "date": photography.completed_at.strftime("%d %b %Y") if photography else None,
            "by_practitioner": photography.completed_by_practitioner if photography else False,
        },
        "botox": {
            "client_signed": botox.client_signed if botox else False,
            "fully_complete": botox.is_fully_complete if botox else False,
            "date": botox.completed_at.strftime("%d %b %Y") if botox else None,
            "id": botox.pk if botox else None,
        },
        "record_cards": record_count,
    })


# ---------------------------------------------------------------------------
# Consultation Form
# ---------------------------------------------------------------------------

@login_required
def consultation_form(request):
    target_user     = _get_target_user(request)
    on_behalf       = _is_practitioner_mode(request)
    existing        = _get_or_none(ConsultationForm, user=target_user)

    if request.method == "POST":
        data = request.POST
        sig  = data.get("signature", "")

        if not sig:
            return JsonResponse({"ok": False, "error": "Signature is required."}, status=400)

        ConsultationForm.objects.create(
            user=target_user,
            completed_by_practitioner=on_behalf,
            practitioner=request.user if on_behalf else None,
            signature=sig,

            full_name=data.get("full_name", ""),
            date_of_birth=data.get("date_of_birth"),
            phone_number=data.get("phone_number", ""),
            email=data.get("email", ""),
            address=data.get("address", ""),
            emergency_contact_name=data.get("emergency_contact_name", ""),
            emergency_contact_phone=data.get("emergency_contact_phone", ""),
            ethnic_origin=data.get("ethnic_origin", ""),
            occupation=data.get("occupation", ""),
            treatment_requested=data.get("treatment_requested", ""),
            treatment_other=data.get("treatment_other", ""),
            body_areas=data.get("body_areas", ""),

            pregnant=bool(data.get("pregnant")),
            pcos_hormonal=bool(data.get("pcos_hormonal")),
            sun_tanned=bool(data.get("sun_tanned")),
            thyroid_condition=bool(data.get("thyroid_condition")),
            skin_pigmentation=bool(data.get("skin_pigmentation")),
            regular_smoker=bool(data.get("regular_smoker")),
            history_of_cancer=bool(data.get("history_of_cancer")),
            psoriasis_eczema=bool(data.get("psoriasis_eczema")),
            diabetes=bool(data.get("diabetes")),
            depression_anxiety=bool(data.get("depression_anxiety")),
            epilepsy=bool(data.get("epilepsy")),
            herpes=bool(data.get("herpes")),
            lymphatic_immune=bool(data.get("lymphatic_immune")),
            high_blood_pressure=bool(data.get("high_blood_pressure")),
            keloid_scarring=bool(data.get("keloid_scarring")),
            photosensitive=bool(data.get("photosensitive")),
            lupus=bool(data.get("lupus")),
            allergies=bool(data.get("allergies")),
            communicable_diseases=bool(data.get("communicable_diseases")),
            alcohol_units_per_week=data.get("alcohol_units_per_week", ""),
            medical_comments=data.get("medical_comments", ""),

            current_medications=data.get("current_medications", ""),
            st_johns_wart=bool(data.get("st_johns_wart")),
            amiodarone=bool(data.get("amiodarone")),
            minocycline=bool(data.get("minocycline")),
            anticoagulants=bool(data.get("anticoagulants")),
            gold_medications=bool(data.get("gold_medications")),
            retinoids=bool(data.get("retinoids")),
            steroids=bool(data.get("steroids")),
            medication_comments=data.get("medication_comments", ""),
            recent_major_treatment=data.get("recent_major_treatment", ""),

            area_has_moles=bool(data.get("area_has_moles")),
            area_has_birthmarks=bool(data.get("area_has_birthmarks")),
            area_has_tattoos=bool(data.get("area_has_tattoos")),
            area_has_permanent_makeup=bool(data.get("area_has_permanent_makeup")),
            area_has_chemical_peel=bool(data.get("area_has_chemical_peel")),
            area_has_botox=bool(data.get("area_has_botox")),
            area_has_fillers=bool(data.get("area_has_fillers")),
            area_has_tanning=bool(data.get("area_has_tanning")),
            skin_disorder=data.get("skin_disorder", ""),
            previous_laser_ipl=data.get("previous_laser_ipl", ""),

            skin_products=data.get("skin_products", ""),
            skin_type=data.get("skin_type", ""),
            current_tan=bool(data.get("current_tan")),
            last_uv_exposure=data.get("last_uv_exposure", ""),
            tanning_injections=bool(data.get("tanning_injections")),
            treatment_goals=data.get("treatment_goals", ""),
            referral_source=data.get("referral_source", ""),

            consent_info_correct=bool(data.get("consent_info_correct")),
            consent_results_vary=bool(data.get("consent_results_vary")),
            consent_multiple_treatments=bool(data.get("consent_multiple_treatments")),
            consent_no_guarantee=bool(data.get("consent_no_guarantee")),
            consent_sun_exposure=bool(data.get("consent_sun_exposure")),
            consent_side_effects=bool(data.get("consent_side_effects")),
            consent_pigmentation=bool(data.get("consent_pigmentation")),
            consent_goggles=bool(data.get("consent_goggles")),
            consent_contact_details=bool(data.get("consent_contact_details")),
            consent_certified=bool(data.get("consent_certified")),

            pretx_how_works=bool(data.get("pretx_how_works")),
            pretx_pre_post_care=bool(data.get("pretx_pre_post_care")),
            pretx_light_products=bool(data.get("pretx_light_products")),
            pretx_num_treatments=bool(data.get("pretx_num_treatments")),
            pretx_clinical_outcome=bool(data.get("pretx_clinical_outcome")),
            pretx_sensation=bool(data.get("pretx_sensation")),
            pretx_side_effects=bool(data.get("pretx_side_effects")),
            pretx_cost=data.get("pretx_cost", ""),
            pretx_photo_taken=bool(data.get("pretx_photo_taken")),
            pretx_comments=data.get("pretx_comments", ""),
            operator_signature=data.get("operator_signature", ""),

            hair_colour=data.get("hair_colour", ""),
            hair_texture=data.get("hair_texture", ""),
            hair_handpiece=data.get("hair_handpiece", ""),
            hair_previous_treatments=data.get("hair_previous_treatments", ""),
            vascular_type=data.get("vascular_type", ""),
            vascular_previous_treatments=data.get("vascular_previous_treatments", ""),
            pigmentation_type=data.get("pigmentation_type", ""),
            pigmentation_previous_treatments=data.get("pigmentation_previous_treatments", ""),
            acne_type=data.get("acne_type", ""),
            acne_previous_treatments=data.get("acne_previous_treatments", ""),
            skin_assessment_type=data.get("skin_assessment_type", ""),
            skin_handpiece=data.get("skin_handpiece", ""),
            skin_previous_treatments=data.get("skin_previous_treatments", ""),
            tattoo_colour=data.get("tattoo_colour", ""),
            tattoo_previous_treatments=data.get("tattoo_previous_treatments", ""),
            fractional_indication=data.get("fractional_indication", ""),
            fractional_comments=data.get("fractional_comments", ""),
        )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True})
        return redirect("accounts:profile")

    return render(request, "forms_system/consultation_form.html", {
        "existing": existing,
        "target_user": target_user,
        "on_behalf": on_behalf,
        "is_practitioner": request.user.is_superuser,
    })


# ---------------------------------------------------------------------------
# Photography Consent
# ---------------------------------------------------------------------------

@login_required
def photography_consent(request):
    target_user = _get_target_user(request)
    on_behalf   = _is_practitioner_mode(request)
    existing    = _get_or_none(PhotographyConsent, user=target_user)

    if request.method == "POST":
        data = request.POST
        sig  = data.get("signature", "")

        if not sig:
            return JsonResponse({"ok": False, "error": "Signature is required."}, status=400)

        PhotographyConsent.objects.create(
            user=target_user,
            completed_by_practitioner=on_behalf,
            practitioner=request.user if on_behalf else None,
            signature=sig,
            full_name=data.get("full_name", ""),
            date_of_birth=data.get("date_of_birth"),
            address=data.get("address", ""),
            consent_1=bool(data.get("consent_1")),
            consent_2=bool(data.get("consent_2")),
            consent_3=bool(data.get("consent_3")),
            consent_4=bool(data.get("consent_4")),
            consent_5=bool(data.get("consent_5")),
        )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True})
        return redirect("accounts:profile")

    return render(request, "forms_system/photography_consent.html", {
        "existing": existing,
        "target_user": target_user,
        "on_behalf": on_behalf,
    })


# ---------------------------------------------------------------------------
# Botox — Step 1 (client)
# ---------------------------------------------------------------------------

@login_required
def botox_client(request):
    target_user = _get_target_user(request)
    on_behalf   = _is_practitioner_mode(request)
    existing    = _get_or_none(BotoxConsentForm, user=target_user)

    if request.method == "POST":
        data = request.POST
        sig  = data.get("signature", "")

        if not sig:
            return JsonResponse({"ok": False, "error": "Signature is required."}, status=400)

        now = timezone.now()

        botox = BotoxConsentForm.objects.create(
            user=target_user,
            completed_by_practitioner=on_behalf,
            practitioner=request.user if on_behalf else None,
            signature=sig,

            full_name=data.get("full_name", ""),
            date_of_birth=data.get("date_of_birth"),
            phone_number=data.get("phone_number", ""),
            email=data.get("email", ""),
            address=data.get("address", ""),
            emergency_contact_name=data.get("emergency_contact_name", ""),
            emergency_contact_phone=data.get("emergency_contact_phone", ""),

            has_allergies=bool(data.get("has_allergies")),
            allergy_details=data.get("allergy_details", ""),
            neuromuscular_disorders=bool(data.get("neuromuscular_disorders")),
            skin_conditions=bool(data.get("skin_conditions")),
            blood_disorders=bool(data.get("blood_disorders")),
            history_of_fainting=bool(data.get("history_of_fainting")),
            other_conditions=data.get("other_conditions", ""),
            current_medications=data.get("current_medications", ""),
            previous_cosmetic_procedures=data.get("previous_cosmetic_procedures", ""),
            botox_allergies=data.get("botox_allergies", ""),

            area_forehead=bool(data.get("area_forehead")),
            area_frown_lines=bool(data.get("area_frown_lines")),
            area_crows_feet=bool(data.get("area_crows_feet")),
            area_other=data.get("area_other", ""),
            expectations=data.get("expectations", ""),

            is_pregnant=bool(data.get("is_pregnant")),
            is_breastfeeding=bool(data.get("is_breastfeeding")),
            has_cold_sores=bool(data.get("has_cold_sores")),
            has_medical_problems=bool(data.get("has_medical_problems")),
            medical_problems_details=data.get("medical_problems_details", ""),
            on_medication=bool(data.get("on_medication")),
            medication_details=data.get("medication_details", ""),
            has_allergies_q2=bool(data.get("has_allergies_q2")),
            allergy_details_q2=data.get("allergy_details_q2", ""),
            previous_procedures=bool(data.get("previous_procedures")),
            previous_procedures_details=data.get("previous_procedures_details", ""),
            yes_details=data.get("yes_details", ""),

            consent_interactions=bool(data.get("consent_interactions")),
            consent_appearance=bool(data.get("consent_appearance")),
            consent_limitations=bool(data.get("consent_limitations")),
            consent_alternatives=bool(data.get("consent_alternatives")),
            consent_followup=bool(data.get("consent_followup")),
            consent_dissatisfaction=bool(data.get("consent_dissatisfaction")),
            consent_agreement=bool(data.get("consent_agreement")),
            consent_privacy_policy=bool(data.get("consent_privacy_policy")),

            client_signed=True,
            client_signed_at=now,
        )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "botox_id": botox.pk})
        return redirect("accounts:profile")

    return render(request, "forms_system/botox_client.html", {
        "existing": existing,
        "target_user": target_user,
        "on_behalf": on_behalf,
    })


# ---------------------------------------------------------------------------
# Botox — Step 2 (operator)
# ---------------------------------------------------------------------------

@staff_required
def botox_operator(request, pk):
    botox = get_object_or_404(BotoxConsentForm, pk=pk)

    if request.method == "POST":
        data = request.POST
        sig  = data.get("operator_signature", "")

        if not sig:
            return JsonResponse(
                {"ok": False, "error": "Operator signature is required."}, status=400
            )

        botox.treatment_notes   = data.get("treatment_notes", "")
        botox.next_appointment  = data.get("next_appointment", "")

        botox.treatment_line_1  = data.get("treatment_line_1", "")
        botox.treatment_price_1 = data.get("treatment_price_1") or None
        botox.treatment_units_1 = data.get("treatment_units_1", "")
        botox.treatment_batch_1 = data.get("treatment_batch_1", "")

        botox.treatment_line_2  = data.get("treatment_line_2", "")
        botox.treatment_price_2 = data.get("treatment_price_2") or None
        botox.treatment_units_2 = data.get("treatment_units_2", "")
        botox.treatment_batch_2 = data.get("treatment_batch_2", "")

        botox.treatment_line_3  = data.get("treatment_line_3", "")
        botox.treatment_price_3 = data.get("treatment_price_3") or None
        botox.treatment_units_3 = data.get("treatment_units_3", "")
        botox.treatment_batch_3 = data.get("treatment_batch_3", "")

        botox.operator_notes       = data.get("operator_notes", "")
        botox.operator_signature   = sig
        botox.operator_signed      = True
        botox.operator_signed_at   = timezone.now()
        botox.operator_signed_by   = request.user
        botox.save()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True})
        return redirect("accounts:profile")

    return render(request, "forms_system/botox_operator.html", {
        "botox": botox,
    })


# ---------------------------------------------------------------------------
# Record Card — new
# ---------------------------------------------------------------------------

@staff_required
def record_card_new(request, user_id):
    target_user = get_object_or_404(User, pk=user_id)
    previous    = (
        RecordCard.objects
        .filter(user=target_user)
        .order_by("-treatment_number")
        .first()
    )

    if request.method == "POST":
        data = request.POST
        sig  = data.get("reconsent_signature", "")

        if not sig:
            return JsonResponse(
                {"ok": False, "error": "Re-consent signature is required."}, status=400
            )

        def decimal_or_none(val):
            try:
                return float(val) if val else None
            except ValueError:
                return None

        RecordCard.objects.create(
            user=target_user,
            date=data.get("date"),
            time=data.get("time"),
            treatment_for=data.get("treatment_for", ""),

            device_remove_650=bool(data.get("device_remove_650")),
            device_rebright_585=bool(data.get("device_rebright_585")),
            device_remove_lp1064=bool(data.get("device_remove_lp1064")),
            device_resurface=bool(data.get("device_resurface")),
            device_remodel=bool(data.get("device_remodel")),
            device_illumifacial=bool(data.get("device_illumifacial")),
            device_remove_q1064=bool(data.get("device_remove_q1064")),
            device_remove_q532=bool(data.get("device_remove_q532")),

            changes_consultation_form=bool(data.get("changes_consultation_form")),
            changes_medication=bool(data.get("changes_medication")),
            changes_uv_exposure=bool(data.get("changes_uv_exposure")),
            consent_settings_change=bool(data.get("consent_settings_change")),
            client_feedback=data.get("client_feedback", ""),

            reconsent_signature=sig,
            reconsent_signed_at=timezone.now(),

            area_1=data.get("area_1",""), skin_type_1=data.get("skin_type_1",""),
            spot_size_1=data.get("spot_size_1",""), fluence_1=data.get("fluence_1",""),
            pulses_1=data.get("pulses_1",""), delay_1=data.get("delay_1",""),
            shots_1=data.get("shots_1",""), cost_1=decimal_or_none(data.get("cost_1")),

            area_2=data.get("area_2",""), skin_type_2=data.get("skin_type_2",""),
            spot_size_2=data.get("spot_size_2",""), fluence_2=data.get("fluence_2",""),
            pulses_2=data.get("pulses_2",""), delay_2=data.get("delay_2",""),
            shots_2=data.get("shots_2",""), cost_2=decimal_or_none(data.get("cost_2")),

            area_3=data.get("area_3",""), skin_type_3=data.get("skin_type_3",""),
            spot_size_3=data.get("spot_size_3",""), fluence_3=data.get("fluence_3",""),
            pulses_3=data.get("pulses_3",""), delay_3=data.get("delay_3",""),
            shots_3=data.get("shots_3",""), cost_3=decimal_or_none(data.get("cost_3")),

            area_4=data.get("area_4",""), skin_type_4=data.get("skin_type_4",""),
            spot_size_4=data.get("spot_size_4",""), fluence_4=data.get("fluence_4",""),
            pulses_4=data.get("pulses_4",""), delay_4=data.get("delay_4",""),
            shots_4=data.get("shots_4",""), cost_4=decimal_or_none(data.get("cost_4")),

            area_5=data.get("area_5",""), skin_type_5=data.get("skin_type_5",""),
            spot_size_5=data.get("spot_size_5",""), fluence_5=data.get("fluence_5",""),
            pulses_5=data.get("pulses_5",""), delay_5=data.get("delay_5",""),
            shots_5=data.get("shots_5",""), cost_5=decimal_or_none(data.get("cost_5")),

            operator_comments=data.get("operator_comments", ""),
            created_by=request.user,
        )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True})
        return redirect("accounts:profile")

    return render(request, "forms_system/record_card_new.html", {
        "target_user": target_user,
        "previous": previous,
    })


# ---------------------------------------------------------------------------
# Record Card — view existing
# ---------------------------------------------------------------------------

@login_required
def record_card_view(request, pk):
    card = get_object_or_404(RecordCard, pk=pk)

    # Clients can only see their own; staff can see all
    if not request.user.is_superuser and card.user != request.user:
        return redirect("accounts:profile")

    return render(request, "forms_system/record_card_view.html", {"card": card})