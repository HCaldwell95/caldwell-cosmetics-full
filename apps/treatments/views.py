from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from .models import Treatment, TreatmentCategory

# Category slugs that have pre/post treatment advice pages
_PRE_POST_NAMES = {
    'anti-wrinkle-treatments': ('forms_system:botox_pre_treatment',  'forms_system:botox_post_treatment'),
    'platelet-rich-plasma-prp': ('forms_system:prp_pre_treatment',   'forms_system:prp_post_treatment'),
    'ipl-hair-removal':         ('forms_system:laser_pre_treatment',  'forms_system:laser_post_treatment'),
}


def _pre_post_context(slug):
    names = _PRE_POST_NAMES.get(slug)
    if names:
        return {
            'pre_treatment_url':  reverse(names[0]),
            'post_treatment_url': reverse(names[1]),
        }
    return {}


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
        **_pre_post_context(slug),
    })


def treatment_detail(request, slug):
    treatment = get_object_or_404(Treatment, slug=slug)

    return render(request, "treatments/treatment_information.html", {
        "treatment": treatment,
        "treatment_template": f"treatments/partials/{treatment.slug}.html",
        **_pre_post_context(treatment.slug),
    })