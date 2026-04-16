from django.shortcuts import render, get_object_or_404
from .models import Treatment

def treatments(request):
    """
    Renders the treatments page displaying all available treatments.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Rendered treatments page template.
    """
    treatments = Treatment.objects.all().order_by('name')  # Fetch all treatments from the database
    return render(request, 'treatments/treatments.html', {'treatments': treatments})

def treatment_card_details(request, slug):
    treatment = get_object_or_404(Treatment, slug=slug)

    # Build the partial template path dynamically
    treatment_template = f"treatments/partials/{treatment.slug}.html"

    return render(request, 'treatments/treatment_information.html', {
        'treatment': treatment,
        'treatment_template': treatment_template,
    })