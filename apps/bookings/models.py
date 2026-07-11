from django.db import models
from django.conf import settings
from apps.treatments.models import Treatment


class Booking(models.Model):

    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
    )

    treatment = models.ForeignKey(
        Treatment,
        on_delete=models.PROTECT,
        related_name="bookings",
    )

    date       = models.DateField()
    start_time = models.TimeField()

    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CONFIRMED,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-start_time"]

        # ⚠️  CHANGE 3: unique_together was ("treatment", "date", "start_time").
        #
        #     That only prevented the exact same treatment being booked twice at
        #     the same time — it did NOT prevent two different treatments
        #     overlapping in the same clinic slot (e.g. a 90-min booking at 09:30
        #     and a 60-min booking at 10:00 on the same day).
        #
        #     Because this is a single-room clinic, overlap protection is handled
        #     entirely in create_booking() via select_for_update() inside a
        #     transaction. A per-treatment uniqueness constraint would give false
        #     confidence that double-bookings are impossible at the DB level when
        #     they are not.
        #
        #     The IntegrityError catch in views.py remains as a last-resort safety
        #     net for any unexpected constraint violations.

    def __str__(self):
        return f"{self.user} — {self.treatment.name} on {self.date} at {self.start_time}"


class ClosedDate(models.Model):
    """
    A single calendar date the clinic is closed (holiday, staff leave, etc.).
    Clients cannot book on these dates; operators may still override via
    the practitioner dashboard.
    """

    date   = models.DateField(unique=True)
    reason = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.date} — {self.reason}" if self.reason else str(self.date)