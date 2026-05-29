from django.shortcuts import render, get_object_or_404
from .models import Treatment, TreatmentCategory


def treatments(request):
    categories = (
        TreatmentCategory.objects
        .filter(is_active=True)
        .prefetch_related("treatments")
        .order_by("order")
    )

    return render(request, "treatments/treatments.html", {
        "categories": categories
    })


def category_detail(request, slug):
    category = get_object_or_404(
        TreatmentCategory.objects.prefetch_related("treatments"),
        slug=slug,
        is_active=True,
    )

    return render(request, "treatments/treatment_information.html", {
        "category": category,
        "treatment_template": f"treatments/partials/{slug}.html",
    })


def treatment_detail(request, slug):
    treatment = get_object_or_404(Treatment, slug=slug)

    return render(request, "treatments/treatment_information.html", {
        "treatment": treatment,
        "treatment_template": f"treatments/partials/{treatment.slug}.html",
    })