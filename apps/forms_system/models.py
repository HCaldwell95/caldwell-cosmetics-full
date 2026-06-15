from django.db import models, transaction
from django.conf import settings


class BaseForm(models.Model):
    """
    Abstract base for all consent forms.
    Stores who completed it, when, and whether a practitioner
    assisted — covering the legal audit trail requirement.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="%(class)s_forms",
    )
    completed_at = models.DateTimeField(auto_now_add=True)
    completed_by_practitioner = models.BooleanField(
        default=False,
        help_text="True if practitioner completed this on behalf of the client.",
    )
    practitioner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_completed_as_practitioner",
        help_text="The staff member who completed this, if applicable.",
    )
    signature = models.TextField(
        help_text="Base64-encoded PNG of the client signature.",
    )

    # ---- Minor / guardian fields ----
    guardian_name         = models.CharField(max_length=200, blank=True)
    guardian_relationship = models.CharField(max_length=100, blank=True)
    guardian_phone        = models.CharField(max_length=20,  blank=True)
    guardian_email        = models.EmailField(blank=True)
    guardian_signature    = models.TextField(blank=True, help_text="Base64-encoded PNG of guardian/parent signature.")

    class Meta:
        abstract = True
        ordering = ["-completed_at"]


class ConsultationForm(BaseForm):
    """
    Dynamix Consultation Form — completed once per client.
    Split into sections matching the paper form exactly.
    """

    # ---- Client information ----
    full_name        = models.CharField(max_length=200)
    date_of_birth    = models.DateField()
    phone_number     = models.CharField(max_length=20, blank=True)
    email            = models.EmailField()
    address          = models.TextField(blank=True)
    emergency_contact_name  = models.CharField(max_length=200, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    ethnic_origin    = models.CharField(max_length=100, blank=True)
    occupation       = models.CharField(max_length=100, blank=True)

    # ---- Treatment requested ----
    TREATMENT_CHOICES = [
        ("hair_removal",  "Hair Removal"),
        ("illumifacial",  "illumiFacial"),
        ("vascular",      "Vascular"),
        ("pigmentation",  "Pigmentation"),
        ("acne",          "Acne"),
        ("laxity",        "Laxity"),
        ("congestion",    "Congestion"),
        ("scarring",      "Scarring"),
        ("resurfacing",   "Resurfacing"),
        ("tattoo_removal","Tattoo Removal"),
        ("other",         "Other"),
    ]
    treatment_requested = models.CharField(
        max_length=20, choices=TREATMENT_CHOICES, blank=True
    )
    treatment_other     = models.CharField(max_length=200, blank=True)
    body_areas          = models.CharField(max_length=200, blank=True)

    # ---- Lifestyle & medical history (checkboxes) ----
    pregnant                  = models.BooleanField(default=False)
    pcos_hormonal             = models.BooleanField(default=False)
    sun_tanned                = models.BooleanField(default=False)
    thyroid_condition         = models.BooleanField(default=False)
    skin_pigmentation         = models.BooleanField(default=False)
    regular_smoker            = models.BooleanField(default=False)
    history_of_cancer         = models.BooleanField(default=False)
    psoriasis_eczema          = models.BooleanField(default=False)
    diabetes                  = models.BooleanField(default=False)
    depression_anxiety        = models.BooleanField(default=False)
    epilepsy                  = models.BooleanField(default=False)
    herpes                    = models.BooleanField(default=False)
    lymphatic_immune          = models.BooleanField(default=False)
    high_blood_pressure       = models.BooleanField(default=False)
    keloid_scarring           = models.BooleanField(default=False)
    photosensitive            = models.BooleanField(default=False)
    lupus                     = models.BooleanField(default=False)
    allergies                 = models.BooleanField(default=False)
    communicable_diseases     = models.BooleanField(default=False)
    alcohol_units_per_week    = models.CharField(max_length=20, blank=True)
    medical_comments          = models.TextField(blank=True)

    # ---- Medications ----
    current_medications       = models.TextField(blank=True)
    st_johns_wart             = models.BooleanField(default=False)
    amiodarone                = models.BooleanField(default=False)
    minocycline               = models.BooleanField(default=False)
    anticoagulants            = models.BooleanField(default=False)
    gold_medications          = models.BooleanField(default=False)
    retinoids                 = models.BooleanField(default=False)
    steroids                  = models.BooleanField(default=False)
    medication_comments       = models.TextField(blank=True)
    recent_major_treatment    = models.TextField(blank=True)

    # ---- Treatment area ----
    area_has_moles            = models.BooleanField(default=False)
    area_has_birthmarks       = models.BooleanField(default=False)
    area_has_tattoos          = models.BooleanField(default=False)
    area_has_permanent_makeup = models.BooleanField(default=False)
    area_has_chemical_peel    = models.BooleanField(default=False)
    area_has_botox            = models.BooleanField(default=False)
    area_has_fillers          = models.BooleanField(default=False)
    area_has_tanning          = models.BooleanField(default=False)
    skin_disorder             = models.TextField(blank=True)
    previous_laser_ipl        = models.TextField(blank=True)

    # ---- Skin ----
    SKIN_TYPE_CHOICES = [
        ("1", "Type 1 – Always burns, never tans"),
        ("2", "Type 2 – Easily burnt, eventually gets a moderate tan"),
        ("3", "Type 3 – Sometimes burns, quickly gets an average tan"),
        ("4", "Type 4 – Rarely burns, quickly gets a deep tan"),
        ("5", "Type 5 – Very rarely burns, consistent tan"),
        ("6", "Type 6 – Never burns, consistent tan"),
    ]
    skin_products         = models.TextField(blank=True)
    skin_type             = models.CharField(
        max_length=1, choices=SKIN_TYPE_CHOICES, blank=True
    )
    current_tan           = models.BooleanField(default=False)
    last_uv_exposure      = models.CharField(max_length=100, blank=True)
    tanning_injections    = models.BooleanField(default=False)
    treatment_goals       = models.TextField(blank=True)
    referral_source       = models.CharField(max_length=100, blank=True)

    # ---- Consent declarations (all must be True to submit) ----
    consent_info_correct         = models.BooleanField(default=False)
    consent_results_vary         = models.BooleanField(default=False)
    consent_multiple_treatments  = models.BooleanField(default=False)
    consent_no_guarantee         = models.BooleanField(default=False)
    consent_sun_exposure         = models.BooleanField(default=False)
    consent_side_effects         = models.BooleanField(default=False)
    consent_pigmentation         = models.BooleanField(default=False)
    consent_goggles              = models.BooleanField(default=False)
    consent_contact_details      = models.BooleanField(default=False)
    consent_certified            = models.BooleanField(default=False)

    # ---- Operator sections (practitioner only) ----
    pretx_how_works         = models.BooleanField(default=False)
    pretx_pre_post_care     = models.BooleanField(default=False)
    pretx_light_products    = models.BooleanField(default=False)
    pretx_num_treatments    = models.BooleanField(default=False)
    pretx_clinical_outcome  = models.BooleanField(default=False)
    pretx_sensation         = models.BooleanField(default=False)
    pretx_side_effects      = models.BooleanField(default=False)
    pretx_cost              = models.CharField(max_length=20, blank=True)
    pretx_photo_taken       = models.BooleanField(default=False)
    pretx_comments          = models.TextField(blank=True)
    operator_signature      = models.TextField(blank=True)

    # ---- Treatment assessment (practitioner only) ----
    # Hair removal
    HAIR_COLOUR_CHOICES = [
        ("black","Black"),("dark_brown","Dark Brown"),("light_brown","Light Brown"),
        ("red","Red"),("blonde","Blonde"),("grey_white","Grey/White"),
    ]
    HAIR_TEXTURE_CHOICES = [
        ("coarse","Coarse"),("medium","Medium"),("fine","Fine"),
    ]
    hair_colour              = models.CharField(max_length=20, choices=HAIR_COLOUR_CHOICES, blank=True)
    hair_texture             = models.CharField(max_length=10, choices=HAIR_TEXTURE_CHOICES, blank=True)
    hair_handpiece           = models.CharField(max_length=50, blank=True)
    hair_previous_treatments = models.TextField(blank=True)

    # Vascular
    VASCULAR_TYPE_CHOICES = [
        ("rosacea","Rosacea"),("thread_veins","Thread Veins"),
        ("spider_nevi","Spider Nevi"),("pws","PWS"),
        ("leg_veins","Leg Veins"),("other","Other"),
    ]
    vascular_type               = models.CharField(max_length=20, choices=VASCULAR_TYPE_CHOICES, blank=True)
    vascular_previous_treatments = models.TextField(blank=True)

    # Pigmentation
    PIGMENTATION_TYPE_CHOICES = [
        ("lentigines","Lentigines (liver spots)"),
        ("freckles","Freckles"),
        ("birthmark","Birthmark"),
    ]
    pigmentation_type               = models.CharField(max_length=20, choices=PIGMENTATION_TYPE_CHOICES, blank=True)
    pigmentation_previous_treatments = models.TextField(blank=True)

    # Acne
    ACNE_TYPE_CHOICES = [
        ("mild","Mild"),("moderate","Moderate"),("severe","Severe"),
    ]
    acne_type               = models.CharField(max_length=10, choices=ACNE_TYPE_CHOICES, blank=True)
    acne_previous_treatments = models.TextField(blank=True)

    # Skin
    skin_assessment_type            = models.CharField(max_length=200, blank=True)
    skin_handpiece                  = models.CharField(max_length=200, blank=True)
    skin_previous_treatments        = models.TextField(blank=True)

    # Tattoo
    tattoo_colour               = models.CharField(max_length=200, blank=True)
    tattoo_previous_treatments  = models.TextField(blank=True)

    # Fractional laser
    fractional_indication       = models.CharField(max_length=200, blank=True)
    fractional_comments         = models.TextField(blank=True)

    class Meta(BaseForm.Meta):
        verbose_name = "Consultation Form"

    def __str__(self):
        return f"Consultation — {self.user.full_name} ({self.completed_at.date()})"


class BotoxConsentForm(BaseForm):
    """
    Botulinum Toxin Consent — two-step.
    Step 1: client section. Step 2: operator section.
    The form is considered complete only when operator_signed is True.
    """

    # ---- Step 1: Client ----
    full_name                   = models.CharField(max_length=200)
    date_of_birth               = models.DateField()
    phone_number                = models.CharField(max_length=20, blank=True)
    email                       = models.EmailField()
    address                     = models.TextField(blank=True)
    emergency_contact_name      = models.CharField(max_length=200, blank=True)
    emergency_contact_phone     = models.CharField(max_length=20, blank=True)

    # Medical history checkboxes
    has_allergies               = models.BooleanField(default=False)
    allergy_details             = models.TextField(blank=True)
    neuromuscular_disorders     = models.BooleanField(default=False)
    skin_conditions             = models.BooleanField(default=False)
    blood_disorders             = models.BooleanField(default=False)
    history_of_fainting         = models.BooleanField(default=False)
    other_conditions            = models.TextField(blank=True)
    current_medications         = models.TextField(blank=True)
    previous_cosmetic_procedures = models.TextField(blank=True)
    botox_allergies             = models.TextField(blank=True)

    # Goals
    area_forehead               = models.BooleanField(default=False)
    area_frown_lines            = models.BooleanField(default=False)
    area_crows_feet             = models.BooleanField(default=False)
    area_other                  = models.CharField(max_length=200, blank=True)
    expectations                = models.TextField(blank=True)

    # Health questions (yes/no)
    is_pregnant                 = models.BooleanField(default=False)
    is_breastfeeding            = models.BooleanField(default=False)
    has_cold_sores              = models.BooleanField(default=False)
    has_medical_problems        = models.BooleanField(default=False)
    medical_problems_details    = models.TextField(blank=True)
    on_medication               = models.BooleanField(default=False)
    medication_details          = models.TextField(blank=True)
    has_allergies_q2            = models.BooleanField(default=False)
    allergy_details_q2          = models.TextField(blank=True)
    previous_procedures         = models.BooleanField(default=False)
    previous_procedures_details = models.TextField(blank=True)
    yes_details                 = models.TextField(
        blank=True,
        help_text="Details for any YES answers above.",
    )

    # Consent declarations
    consent_interactions        = models.BooleanField(default=False)
    consent_appearance          = models.BooleanField(default=False)
    consent_limitations         = models.BooleanField(default=False)
    consent_alternatives        = models.BooleanField(default=False)
    consent_followup            = models.BooleanField(default=False)
    consent_dissatisfaction     = models.BooleanField(default=False)
    consent_agreement           = models.BooleanField(default=False)
    consent_privacy_policy      = models.BooleanField(default=False)

    # Step 1 complete flag
    client_signed               = models.BooleanField(default=False)
    client_signed_at            = models.DateTimeField(null=True, blank=True)

    # ---- Step 2: Operator ----
    treatment_notes             = models.TextField(blank=True)
    next_appointment            = models.CharField(max_length=200, blank=True)

    # Treatment table rows (up to 4 lines)
    treatment_line_1            = models.CharField(max_length=300, blank=True)
    treatment_price_1           = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    treatment_units_1           = models.CharField(max_length=50, blank=True)
    treatment_batch_1           = models.CharField(max_length=100, blank=True)

    treatment_line_2            = models.CharField(max_length=300, blank=True)
    treatment_price_2           = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    treatment_units_2           = models.CharField(max_length=50, blank=True)
    treatment_batch_2           = models.CharField(max_length=100, blank=True)

    treatment_line_3            = models.CharField(max_length=300, blank=True)
    treatment_price_3           = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    treatment_units_3           = models.CharField(max_length=50, blank=True)
    treatment_batch_3           = models.CharField(max_length=100, blank=True)

    operator_notes              = models.TextField(blank=True)

    # ---- Step 2: Treatment areas (facial mapping) ----
    treatment_product_lot       = models.CharField(max_length=200, blank=True)
    units_forehead              = models.CharField(max_length=10, blank=True)
    units_glabella              = models.CharField(max_length=10, blank=True)
    units_crows_feet            = models.CharField(max_length=10, blank=True)
    units_jelly_roll            = models.CharField(max_length=10, blank=True)
    units_bunny_lines           = models.CharField(max_length=10, blank=True)
    units_gummy_smile           = models.CharField(max_length=10, blank=True)
    units_smokers_lines         = models.CharField(max_length=10, blank=True)
    units_lip_flip              = models.CharField(max_length=10, blank=True)
    units_dao_jowls             = models.CharField(max_length=10, blank=True)
    units_chin                  = models.CharField(max_length=10, blank=True)
    units_masseter              = models.CharField(max_length=10, blank=True)
    units_neck_bands            = models.CharField(max_length=10, blank=True)
    units_total                 = models.CharField(max_length=10, blank=True)
    treatment_cost              = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    operator_signature          = models.TextField(blank=True)
    operator_signed             = models.BooleanField(default=False)
    operator_signed_at          = models.DateTimeField(null=True, blank=True)
    operator_signed_by          = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="botox_operator_completions",
    )

    @property
    def is_fully_complete(self):
        return self.client_signed and self.operator_signed

    class Meta(BaseForm.Meta):
        verbose_name = "Botulinum Toxin Consent Form"

    def __str__(self):
        return f"Botox Consent — {self.user.full_name} ({self.completed_at.date()})"


class PhotographyConsent(BaseForm):
    """Photography and digital image consent — completed once."""

    full_name     = models.CharField(max_length=200)
    date_of_birth = models.DateField()
    address       = models.TextField(blank=True)

    consent_1 = models.BooleanField(
        default=False,
        help_text="Consent for photographs for records and future care planning.",
    )
    consent_2 = models.BooleanField(
        default=False,
        help_text="Consent to share with other professionals for treatment planning.",
    )
    consent_3 = models.BooleanField(
        default=False,
        help_text="Consent for anonymous use in patient education.",
    )
    consent_4 = models.BooleanField(
        default=False,
        help_text="Consent for anonymous use on website/social media.",
    )
    consent_5 = models.BooleanField(
        default=False,
        help_text="Consent for use with identity/name in practice and advertising.",
    )

    class Meta(BaseForm.Meta):
        verbose_name = "Photography Consent"

    def __str__(self):
        return f"Photography Consent — {self.user.full_name} ({self.completed_at.date()})"


class RecordCard(models.Model):
    """
    Dynamix Record Card — one per treatment session.
    Practitioner-only. Append-only (never edited after save).
    Each card links to the previous one for the same client.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="record_cards",
    )
    treatment_number = models.PositiveIntegerField(
        help_text="Auto-incremented per client.",
    )
    date        = models.DateField()
    time        = models.TimeField()
    treatment_for = models.CharField(max_length=200, blank=True)

    # Device selection
    device_remove_650    = models.BooleanField(default=False)
    device_rebright_585  = models.BooleanField(default=False)
    device_remove_lp1064 = models.BooleanField(default=False)
    device_resurface     = models.BooleanField(default=False)
    device_remodel       = models.BooleanField(default=False)
    device_illumifacial  = models.BooleanField(default=False)
    device_remove_q1064  = models.BooleanField(default=False)
    device_remove_q532   = models.BooleanField(default=False)

    # Changes since last visit
    changes_consultation_form   = models.BooleanField(
        default=False, help_text="Changes to consultation form?"
    )
    changes_medication          = models.BooleanField(
        default=False, help_text="Changes to medication/medical history?"
    )
    changes_uv_exposure         = models.BooleanField(
        default=False, help_text="Recent UV exposure or fake tan?"
    )
    consent_settings_change     = models.BooleanField(
        default=False,
        help_text="Client consents to settings being changed to meet clinical endpoints.",
    )
    client_feedback             = models.TextField(blank=True)

    # Re-consent signature
    reconsent_signature         = models.TextField(
        help_text="Base64 PNG of client re-consent signature.",
    )
    reconsent_signed_at         = models.DateTimeField()

    # Treatment areas (up to 5 rows matching the paper form)
    area_1          = models.CharField(max_length=100, blank=True)
    skin_type_1     = models.CharField(max_length=20, blank=True)
    spot_size_1     = models.CharField(max_length=20, blank=True)
    fluence_1       = models.CharField(max_length=20, blank=True)
    pulses_1        = models.CharField(max_length=20, blank=True)
    delay_1         = models.CharField(max_length=20, blank=True)
    shots_1         = models.CharField(max_length=20, blank=True)
    cost_1          = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    area_2          = models.CharField(max_length=100, blank=True)
    skin_type_2     = models.CharField(max_length=20, blank=True)
    spot_size_2     = models.CharField(max_length=20, blank=True)
    fluence_2       = models.CharField(max_length=20, blank=True)
    pulses_2        = models.CharField(max_length=20, blank=True)
    delay_2         = models.CharField(max_length=20, blank=True)
    shots_2         = models.CharField(max_length=20, blank=True)
    cost_2          = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    area_3          = models.CharField(max_length=100, blank=True)
    skin_type_3     = models.CharField(max_length=20, blank=True)
    spot_size_3     = models.CharField(max_length=20, blank=True)
    fluence_3       = models.CharField(max_length=20, blank=True)
    pulses_3        = models.CharField(max_length=20, blank=True)
    delay_3         = models.CharField(max_length=20, blank=True)
    shots_3         = models.CharField(max_length=20, blank=True)
    cost_3          = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    area_4          = models.CharField(max_length=100, blank=True)
    skin_type_4     = models.CharField(max_length=20, blank=True)
    spot_size_4     = models.CharField(max_length=20, blank=True)
    fluence_4       = models.CharField(max_length=20, blank=True)
    pulses_4        = models.CharField(max_length=20, blank=True)
    delay_4         = models.CharField(max_length=20, blank=True)
    shots_4         = models.CharField(max_length=20, blank=True)
    cost_4          = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    area_5          = models.CharField(max_length=100, blank=True)
    skin_type_5     = models.CharField(max_length=20, blank=True)
    spot_size_5     = models.CharField(max_length=100, blank=True)
    fluence_5       = models.CharField(max_length=20, blank=True)
    pulses_5        = models.CharField(max_length=20, blank=True)
    delay_5         = models.CharField(max_length=20, blank=True)
    shots_5         = models.CharField(max_length=20, blank=True)
    cost_5          = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    operator_comments   = models.TextField(blank=True)
    created_by          = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="record_cards_created",
    )
    created_at          = models.DateTimeField(auto_now_add=True)

    # Guardian (minors only)
    guardian_name         = models.CharField(max_length=200, blank=True)
    guardian_relationship = models.CharField(max_length=100, blank=True)
    guardian_phone        = models.CharField(max_length=20,  blank=True)
    guardian_email        = models.EmailField(blank=True)
    guardian_signature    = models.TextField(blank=True)

    class Meta:
        ordering            = ["-date", "-time"]
        unique_together     = ("user", "treatment_number")

    def __str__(self):
        return f"Record Card #{self.treatment_number} — {self.user.full_name} ({self.date})"

    def save(self, *args, **kwargs):
        if not self.pk and not self.treatment_number:
            with transaction.atomic():
                last = (
                    RecordCard.objects
                    .select_for_update()
                    .filter(user=self.user)
                    .order_by("-treatment_number")
                    .first()
                )
                self.treatment_number = (last.treatment_number + 1) if last else 1
                super().save(*args, **kwargs)
            return
        super().save(*args, **kwargs)


class PRPConsentForm(BaseForm):
    """
    PRP (Platelet-Rich Plasma) Consent — two-step.
    Step 1: client section. Step 2: operator section.
    """

    # ---- Step 1: Client ----
    full_name                   = models.CharField(max_length=200)
    date_of_birth               = models.DateField()
    phone_number                = models.CharField(max_length=20, blank=True)
    email                       = models.EmailField()
    address                     = models.TextField(blank=True)
    emergency_contact_name      = models.CharField(max_length=200, blank=True)
    emergency_contact_phone     = models.CharField(max_length=20, blank=True)

    # Medical history checkboxes
    blood_disorders             = models.BooleanField(default=False)
    on_anticoagulants           = models.BooleanField(default=False)
    active_infection            = models.BooleanField(default=False)
    autoimmune_disease          = models.BooleanField(default=False)
    history_of_cancer           = models.BooleanField(default=False)
    skin_conditions             = models.BooleanField(default=False)
    recent_vaccination          = models.BooleanField(default=False)
    communicable_diseases       = models.BooleanField(default=False)
    keloid_scarring             = models.BooleanField(default=False)
    current_medications         = models.TextField(blank=True)
    other_conditions            = models.TextField(blank=True)

    # Treatment area / goals
    treatment_areas             = models.CharField(max_length=300, blank=True)
    expectations                = models.TextField(blank=True)

    # Health questions (yes/no)
    is_pregnant                 = models.BooleanField(default=False)
    is_breastfeeding            = models.BooleanField(default=False)
    has_medical_problems        = models.BooleanField(default=False)
    on_medication               = models.BooleanField(default=False)
    has_allergies               = models.BooleanField(default=False)
    previous_prp                = models.BooleanField(default=False)
    yes_details                 = models.TextField(blank=True)

    # Consent declarations
    consent_procedure           = models.BooleanField(default=False)
    consent_risks               = models.BooleanField(default=False)
    consent_results             = models.BooleanField(default=False)
    consent_aftercare           = models.BooleanField(default=False)
    consent_photos              = models.BooleanField(default=False)
    consent_privacy             = models.BooleanField(default=False)
    consent_agreement           = models.BooleanField(default=False)

    # Step 1 complete flag
    client_signed               = models.BooleanField(default=False)
    client_signed_at            = models.DateTimeField(null=True, blank=True)

    # ---- Step 2: Operator ----
    product_name                = models.CharField(max_length=200, blank=True)
    product_batch               = models.CharField(max_length=200, blank=True)
    vials_drawn                 = models.CharField(max_length=20, blank=True)
    centrifuge_details          = models.CharField(max_length=200, blank=True)
    application_method          = models.CharField(max_length=200, blank=True)
    treatment_areas_operator    = models.TextField(blank=True)
    next_appointment            = models.CharField(max_length=200, blank=True)
    treatment_cost              = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    operator_notes              = models.TextField(blank=True)
    operator_signature          = models.TextField(blank=True)
    operator_signed             = models.BooleanField(default=False)
    operator_signed_at          = models.DateTimeField(null=True, blank=True)
    operator_signed_by          = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="prp_operator_completions",
    )

    @property
    def is_fully_complete(self):
        return self.client_signed and self.operator_signed

    class Meta(BaseForm.Meta):
        verbose_name = "PRP Consent Form"

    def __str__(self):
        return f"PRP Consent — {self.user.full_name} ({self.completed_at.date()})"


class LaserReConsent(models.Model):
    """
    Standalone laser re-consent — completed at each laser appointment.
    Practitioner-assisted: client signs, operator countersigns.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="laser_reconsents",
    )
    completed_at = models.DateTimeField(auto_now_add=True)
    practitioner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="laser_reconsents_as_practitioner",
    )

    # Pre-treatment checks
    changes_consultation_form   = models.BooleanField(default=False)
    changes_medication          = models.BooleanField(default=False)
    changes_uv_exposure         = models.BooleanField(default=False)
    active_tan                  = models.BooleanField(default=False)
    changes_detail              = models.TextField(blank=True)

    # Client
    client_feedback             = models.TextField(blank=True)
    consent_proceed             = models.BooleanField(default=False)
    client_signature            = models.TextField()
    client_signed_at            = models.DateTimeField(null=True, blank=True)

    # Operator
    treatment_notes             = models.TextField(blank=True)
    operator_signature          = models.TextField(blank=True)
    operator_signed             = models.BooleanField(default=False)
    operator_signed_at          = models.DateTimeField(null=True, blank=True)

    # Guardian (minors only)
    guardian_name         = models.CharField(max_length=200, blank=True)
    guardian_relationship = models.CharField(max_length=100, blank=True)
    guardian_phone        = models.CharField(max_length=20,  blank=True)
    guardian_email        = models.EmailField(blank=True)
    guardian_signature    = models.TextField(blank=True)

    class Meta:
        ordering = ["-completed_at"]
        verbose_name = "Laser Re-Consent"

    def __str__(self):
        return f"Laser Re-Consent — {self.user.full_name} ({self.completed_at.date()})"