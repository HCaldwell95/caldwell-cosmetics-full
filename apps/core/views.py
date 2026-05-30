from django.shortcuts import render


def home(request):
    return render(request, 'core/home.html')

def dashboard(request):
    return render(request, "core/dashboard.html")

def privacy(request):
    return render(request, "core/privacy.html")

def terms(request):
    return render(request, "core/terms.html")

def cookies(request):
    return render(request, "core/cookies.html")

def myjourney(request):
    return render(request, "core/myjourney.html")