from django.db import models, transaction
from django.conf import settings

from cloudinary.models import CloudinaryField


class Notification(models.Model):
    # --- Consent form types ---
    FORM_CONSULTATION    = 'consultation'
    FORM_PHOTOGRAPHY     = 'photography'
    FORM_BOTOX           = 'botox'
    FORM_PRP             = 'prp'
    FORM_LASER_RECONSENT = 'laser_reconsent'  # archived standalone re-consents
    FORM_RECORD_CARD     = 'record_card'
    FORM_BOTOX_PRESCRIBED = 'botox_prescribed'

    # --- Booking types ---
    BOOKING_CREATED   = 'booking_created'
    BOOKING_CANCELLED = 'booking_cancelled'
    BOOKING_AMENDED   = 'booking_amended'

    BOOKING_TYPES = {BOOKING_CREATED, BOOKING_CANCELLED, BOOKING_AMENDED}

    FORM_TYPE_LABELS = {
        FORM_CONSULTATION:    'Laser Consultation',
        FORM_PHOTOGRAPHY:     'Photography Consent',
        FORM_BOTOX:           'Botox Consent & Prescription',
        FORM_PRP:             'PRP Consent',
        FORM_LASER_RECONSENT: 'Laser Re-Consent',
        FORM_RECORD_CARD:     'Laser Re-Consent',
        FORM_BOTOX_PRESCRIBED: 'Botox Prescription',
        BOOKING_CREATED:      'New Booking',
        BOOKING_CANCELLED:    'Booking Cancelled',
        BOOKING_AMENDED:      'Booking Amended',
    }

    FORM_TYPE_CHOICES = [(k, v) for k, v in FORM_TYPE_LABELS.items()]

    client       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='form_notifications',
    )
    form_type    = models.CharField(max_length=30, choices=FORM_TYPE_CHOICES)
    form_id      = models.PositiveIntegerField()
    message_text = models.TextField(blank=True, default='')
    is_read      = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def form_label(self):
        return self.FORM_TYPE_LABELS.get(self.form_type, self.form_type)

    @property
    def message(self):
        if self.message_text:
            return self.message_text
        return f"{self.client.full_name} completed a {self.form_label}"

    @property
    def form_url(self):
        if self.form_type in self.BOOKING_TYPES:
            return '/dashboard/'
        urls = {
            self.FORM_CONSULTATION:    f'/forms/consultation/{self.client_id}/view/?form_pk={self.form_id}',
            self.FORM_PHOTOGRAPHY:     f'/forms/photography/{self.form_id}/operator/',
            self.FORM_BOTOX:           f'/forms/botox/{self.form_id}/operator/',
            self.FORM_BOTOX_PRESCRIBED: f'/forms/botox/{self.form_id}/operator/',
            self.FORM_PRP:             f'/forms/prp/{self.form_id}/operator/',
            self.FORM_LASER_RECONSENT: f'/forms/laser/{self.form_id}/view/',
            self.FORM_RECORD_CARD:     f'/forms/records/{self.form_id}/edit/',
        }
        return urls.get(self.form_type, '#')


class ClientNote(models.Model):
    """Operator-only notes attached to a client. Numbered per client, append-only."""

    user    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="client_notes",
    )
    author  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="authored_notes",
    )
    number     = models.PositiveIntegerField(help_text="Auto-incremented per client.")
    title      = models.CharField(max_length=200)
    content    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering        = ["-created_at"]
        unique_together = [("user", "number")]

    def __str__(self):
        return f"Note #{self.number} — {self.user} ({self.created_at.date()})"

    def save(self, *args, **kwargs):
        if not self.pk and not self.number:
            with transaction.atomic():
                last = (
                    ClientNote.objects
                    .select_for_update()
                    .filter(user=self.user)
                    .order_by("-number")
                    .first()
                )
                self.number = (last.number + 1) if last else 1
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Progress photos — uploaded by the practitioner, shown to the client on
# their profile page, grouped by treatment date.
# ---------------------------------------------------------------------------

class ProgressPhotoSet(models.Model):
    """One treatment date's photos for a client."""

    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="photo_sets",
    )
    date       = models.DateField()
    treatment  = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering        = ["-date", "-pk"]
        unique_together = [("user", "date", "treatment")]

    def __str__(self):
        return f"Photos — {self.user} ({self.date}{', ' + self.treatment if self.treatment else ''})"

    def ordered_photos(self):
        """Before photos first, then after, then unlabelled — each oldest first."""
        return sorted(self.photos.all(), key=lambda p: (ProgressPhoto.LABEL_ORDER[p.label], p.pk))


class ProgressPhoto(models.Model):
    class Label(models.TextChoices):
        BEFORE = "before", "Before"
        AFTER  = "after",  "After"
        NONE   = "",       "No label"

    LABEL_ORDER = {Label.BEFORE: 0, Label.AFTER: 1, Label.NONE: 2}

    photo_set   = models.ForeignKey(ProgressPhotoSet, on_delete=models.CASCADE, related_name="photos")
    # Clinical photos are stored privately: they're only reachable through
    # signed links that this site generates (see `url`).
    image       = CloudinaryField("image", type="authenticated", folder="client_progress_photos")
    label       = models.CharField(max_length=10, choices=Label.choices, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["pk"]

    def __str__(self):
        return f"{self.get_label_display()} photo — {self.photo_set}"

    def url(self, width):
        return self.image.build_url(
            sign_url=True, secure=True, width=width, crop="limit",
            quality="auto", fetch_format="auto",
        )

    @property
    def thumb_url(self):
        return self.url(900)

    @property
    def full_url(self):
        return self.url(2000)
