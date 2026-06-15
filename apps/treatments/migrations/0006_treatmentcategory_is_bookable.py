from django.db import migrations, models


def flag_homecare_not_bookable(apps, schema_editor):
    TreatmentCategory = apps.get_model("treatments", "TreatmentCategory")
    TreatmentCategory.objects.filter(slug="prescribed-homecare").update(is_bookable=False)


class Migration(migrations.Migration):

    dependencies = [
        ("treatments", "0005_alter_treatment_options_alter_treatmentgroup_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="treatmentcategory",
            name="is_bookable",
            field=models.BooleanField(
                default=True,
                help_text="Uncheck to hide this category from the booking form (the content page remains visible)",
            ),
        ),
        migrations.RunPython(flag_homecare_not_bookable, migrations.RunPython.noop),
    ]
