from django.db import models, transaction
from django.conf import settings


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
