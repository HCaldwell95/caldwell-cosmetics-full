from django.db import migrations
from django.db.models import F


def lock_existing_forms(apps, schema_editor):
    """
    Before the shared lifecycle, these forms were final as soon as they were
    saved (or, for PRP, once the operator signed). Lock them as completed so
    nothing already on file can be edited.
    """
    for model_name, date_field, by_field in (
        ("ConsultationForm",   "completed_at", "practitioner"),
        ("PhotographyConsent", "completed_at", "practitioner"),
        ("LaserReConsent",     "completed_at", "practitioner"),
        ("RecordCard",         "created_at",   "created_by"),
    ):
        Model = apps.get_model("forms_system", model_name)
        Model.objects.filter(finalised=False, withdrawn=False).update(
            finalised=True, finalised_at=F(date_field), finalised_by=F(by_field),
        )

    PRPConsentForm = apps.get_model("forms_system", "PRPConsentForm")
    PRPConsentForm.objects.filter(client_signed=True, operator_signed=True, finalised=False).update(
        finalised=True, finalised_at=F("operator_signed_at"), finalised_by=F("operator_signed_by"),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("forms_system", "0011_shared_form_lifecycle"),
    ]

    operations = [
        # Not reversed: unlocking completed records should be deliberate.
        migrations.RunPython(lock_existing_forms, migrations.RunPython.noop),
    ]
