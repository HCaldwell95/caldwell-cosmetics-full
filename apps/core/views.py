from django.shortcuts import render
from apps.treatments.models import TreatmentCategory


def home(request):
    marquee_categories = TreatmentCategory.objects.filter(is_active=True).order_by('order', 'name')
    return render(request, 'core/home.html', {'marquee_categories': marquee_categories})

def dashboard(request):
    return render(request, "dashboard/dashboard.html")

def privacy(request):
    return render(request, "core/privacy.html")

def terms(request):
    return render(request, "core/terms.html")

def cookies(request):
    return render(request, "core/cookies.html")

def myjourney(request):
    return render(request, "core/myjourney.html")

def skin_journey(request):
    return render(request, "core/skin_journey.html")

def phformula(request):
    return render(request, "core/phformula.html")

def lynton(request):
    return render(request, "core/lynton.html")