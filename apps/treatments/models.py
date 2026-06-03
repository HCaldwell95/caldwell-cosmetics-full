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


class TreatmentGroup(models.Model):
    category = models.ForeignKey(
        TreatmentCategory,
        on_delete=models.CASCADE,
        related_name='groups'
    )
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0, help_text="Controls display order within a category")

    class Meta:
        ordering = ['category__order', 'order', 'name']
        unique_together = [('category', 'name')]

    def __str__(self):
        return self.name


class Treatment(models.Model):
    category = models.ForeignKey(
        TreatmentCategory,
        on_delete=models.CASCADE,
        related_name="treatments"
    )

    name = models.CharField(max_length=200)
    slug = models.SlugField(blank=True)

    group = models.ForeignKey(
        TreatmentGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='treatments',
        help_text="Optional subgroup within a category, e.g. 'Face', 'Body'. "
                  "Cards with the same group are displayed together under a heading."
    )

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
        ordering = ['category__order', 'category__id', 'group__order', 'group__name', 'order', 'name']
        # Allows "Chest" to exist in both IPL Hair Removal and Skin Rejuvenation
        unique_together = [('name', 'category')]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            # Include category slug prefix to avoid slug clashes across categories
            category_prefix = slugify(self.category.name) if self.category_id else ''
            self.slug = f"{category_prefix}-{slugify(self.name)}" if category_prefix else slugify(self.name)
        super().save(*args, **kwargs)