from django.db import models
from django.utils.text import slugify
from cloudinary.models import CloudinaryField

class Treatment(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    image = CloudinaryField('image')
    summary = models.TextField(blank=True, help_text="Short description shown on the card (optional)")
    order = models.PositiveIntegerField(default=0, help_text="Controls display order")
    is_active = models.BooleanField(default=True, help_text="Uncheck to hide from the page")

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)