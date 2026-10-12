"""
Progress photos: the practitioner uploads and manages a client's photos,
grouped by treatment date; the client sees them on their profile page.
"""

import logging
from datetime import date

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.permissions import practitioner_required
from apps.forms_system.models import PhotographyConsent
from apps.treatments.models import Treatment
from .models import ProgressPhoto, ProgressPhotoSet

logger = logging.getLogger(__name__)
User   = get_user_model()

MAX_FILES     = 20
MAX_FILE_SIZE = 20 * 1024 * 1024
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif")


def photo_sets_for(user):
    """The client's photo sets that have photos, newest first, each with `ordered` photos."""
    sets = list(ProgressPhotoSet.objects.filter(user=user, photos__isnull=False).distinct().prefetch_related("photos"))
    for s in sets:
        s.ordered = s.ordered_photos()
    return sets


def _is_image(f):
    return (f.content_type or "").startswith("image/") or f.name.lower().endswith(IMAGE_EXTENSIONS)


def _parse_set_details(data):
    """(date, treatment, error) from the date / treatment fields."""
    try:
        taken_on = date.fromisoformat(data.get("date", ""))
    except ValueError:
        return None, "", "Please choose the date the photos were taken."
    if taken_on > timezone.localdate():
        return None, "", "The date can't be in the future."
    return taken_on, data.get("treatment", "").strip()[:200], None


def _upload(request, client):
    files = request.FILES.getlist("images")
    taken_on, treatment, error = _parse_set_details(request.POST)
    if not error and not files:
        error = "Please choose at least one photo."
    if not error and len(files) > MAX_FILES:
        error = f"Please upload up to {MAX_FILES} photos at a time."
    if not error:
        bad = [f.name for f in files if not _is_image(f) or f.size > MAX_FILE_SIZE]
        if bad:
            error = f"These aren't images under {MAX_FILE_SIZE // (1024 * 1024)}MB: {', '.join(bad)}"
    if error:
        return error

    photo_set, _ = ProgressPhotoSet.objects.get_or_create(
        user=client, date=taken_on, treatment=treatment,
        defaults={"created_by": request.user},
    )
    labels = {choice for choice, _ in ProgressPhoto.Label.choices}
    saved = 0
    for i, f in enumerate(files):
        label = request.POST.get(f"label_{i}", request.POST.get("default_label", ""))
        try:
            ProgressPhoto.objects.create(
                photo_set=photo_set, image=f, uploaded_by=request.user,
                label=label if label in labels else "",
            )
            saved += 1
        except Exception:  # noqa: BLE001 — a failed upload shouldn't lose the rest
            logger.exception("Progress photo upload failed for %s", f.name)
            messages.error(request, f"{f.name} couldn't be uploaded. Please try it again.")
    if saved:
        messages.success(request, f"{saved} photo{'s' if saved != 1 else ''} added.")
    return None


@practitioner_required
def client_photos(request, pk):
    """Upload photos for a client, and relabel / move / delete existing ones."""
    client = get_object_or_404(User, pk=pk)
    error  = None

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "upload":
            error = _upload(request, client)

        elif action == "relabel":
            photo = get_object_or_404(ProgressPhoto, pk=request.POST.get("photo"), photo_set__user=client)
            label = request.POST.get("label", "")
            if label in ProgressPhoto.Label.values:
                photo.label = label
                photo.save(update_fields=["label"])

        elif action == "delete_photo":
            photo = get_object_or_404(ProgressPhoto, pk=request.POST.get("photo"), photo_set__user=client)
            photo_set = photo.photo_set
            photo.delete()
            if not photo_set.photos.exists():
                photo_set.delete()
            messages.success(request, "Photo deleted.")

        elif action == "edit_set":
            photo_set = get_object_or_404(ProgressPhotoSet, pk=request.POST.get("set"), user=client)
            taken_on, treatment, error = _parse_set_details(request.POST)
            clash = ProgressPhotoSet.objects.filter(user=client, date=taken_on, treatment=treatment).exclude(pk=photo_set.pk)
            if not error and clash.exists():
                error = "There's already a set of photos for that date and treatment."
            if not error:
                photo_set.date, photo_set.treatment = taken_on, treatment
                photo_set.save(update_fields=["date", "treatment"])
                messages.success(request, "Details updated.")

        if not error:
            return redirect("dashboard:client_photos", pk=client.pk)

    return render(request, "dashboard/client_photos.html", {
        "client":      client,
        "photo_sets":  photo_sets_for(client),
        "treatments":  Treatment.objects.order_by("name").values_list("name", flat=True).distinct(),
        "labels":      ProgressPhoto.Label.choices,
        # The client gives consent by signing — it needn't be completed yet.
        "has_consent": PhotographyConsent.objects.filter(user=client, withdrawn=False).exists(),
        "today":       timezone.localdate(),
        "error":       error,
        "max_files":   MAX_FILES,
    }, status=400 if error else 200)
