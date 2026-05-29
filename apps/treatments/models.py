from django.db import models
from django.core.validators import RegexValidator
from django.utils.text import slugify
from cloudinary.models import CloudinaryField

hex_colour_validator = RegexValidator(
    regex=r'^#[0-9A-Fa-f]{6}$',
    message='Enter a valid hex colour, e.g. #A3B4C5'
)

class TreatmentCategory(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    image = CloudinaryField('image')

    colour = models.CharField(
        max_length=7,
        default='#7F77DD',
        validators=[hex_colour_validator],
        help_text='Hex colour code for dashboard display, e.g. #A3B4C5',
    )
    summary = models.TextField(
        blank=True,
        help_text="Short description shown on the card (optional)"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Controls display order"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Uncheck to hide from the page"
    )

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Treatment(models.Model):
    category = models.ForeignKey(
        TreatmentCategory,
        on_delete=models.CASCADE,
        related_name="treatments"
    )

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)

    summary = models.TextField(blank=True)

    duration_minutes = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2)

    requires_deposit = models.BooleanField(default=False)
    deposit_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )

    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['category__order', 'order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)