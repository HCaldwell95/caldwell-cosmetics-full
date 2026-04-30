from django.shortcuts import render, redirect
from django.http import HttpResponse

from apps.treatments.models import Treatment, Category

def overview(request):
    treatments = Treatment.objects.select_related('category').all()
    categories = Category.objects.all()

    context = {
        "treatments": treatments,
        "categories": categories,
        "booked_slots_json": {},  # keep this for now
    }

    return render(request, "bookings/overview.html", context)

def create_booking(request):
    if request.method == "POST":
        treatment_id = request.POST.get("treatment_id")
        date = request.POST.get("date")
        time = request.POST.get("start_time")

        # TEMP: just confirm it's working
        return HttpResponse(f"Booking received: {treatment_id} on {date} at {time}")

    return redirect("bookings:overview")