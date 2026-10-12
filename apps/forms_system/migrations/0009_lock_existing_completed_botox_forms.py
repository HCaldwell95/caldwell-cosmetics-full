from django.db import migrations
from django.db.models import F


def lock_completed_forms(apps, schema_editor):
    """
    Forms signed by both client and operator before completion existed were
    already treated as complete — lock them so they can't be edited.
    """
    BotoxConsentForm = apps.get_model("forms_system", "BotoxConsentForm")
    BotoxConsentForm.objects.filter(client_signed=True, operator_signed=True, finalised=False).update(
        finalised=True,
        finalised_at=F("operator_signed_at"),
        finalised_by=F("operator_signed_by"),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("forms_system", "0008_botox_completion_and_history"),
    ]

    operations = [
        # Not reversed: unlocking completed medical records should be deliberate.
        migrations.RunPython(lock_completed_forms, migrations.RunPython.noop),
    ]
