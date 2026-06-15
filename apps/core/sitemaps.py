from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.treatments.models import Treatment, TreatmentCategory


class StaticPageSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.8
    protocol = "https"

    pages = [
        ("core:home",        1.0,  "weekly"),
        ("treatments:treatments", 0.9, "weekly"),
        ("core:skin_journey",     0.7, "monthly"),
        ("core:phformula",        0.7, "monthly"),
        ("core:lynton",           0.7, "monthly"),
        ("core:myjourney",        0.6, "monthly"),
        ("core:privacy",          0.3, "yearly"),
        ("core:terms",            0.3, "yearly"),
        ("core:cookies",          0.3, "yearly"),
    ]

    def items(self):
        return self.pages

    def location(self, item):
        return reverse(item[0])

    def priority(self, item):
        return item[1]

    def changefreq(self, item):
        return item[2]


class TreatmentCategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    protocol = "https"

    def items(self):
        return TreatmentCategory.objects.filter(is_active=True)

    def location(self, obj):
        return reverse("treatments:category_detail", kwargs={"slug": obj.slug})


class TreatmentSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7
    protocol = "https"

    def items(self):
        return Treatment.objects.filter(is_active=True)

    def location(self, obj):
        return reverse("treatments:treatment_detail", kwargs={"slug": obj.slug})


sitemaps = {
    "static":     StaticPageSitemap(),
    "categories": TreatmentCategorySitemap(),
    "treatments": TreatmentSitemap(),
}
