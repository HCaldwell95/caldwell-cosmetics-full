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

    date = models.DateField()
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
        # Prevent double-booking the same treatment at the same time
        unique_together = ("treatment", "date", "start_time")

    def __str__(self):
        return f"{self.user} — {self.treatment.name} on {self.date} at {self.start_time}"