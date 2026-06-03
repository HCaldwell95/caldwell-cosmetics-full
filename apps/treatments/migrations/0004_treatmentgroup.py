import django.db.models.deletion
from django.db import migrations, models


def populate_groups(apps, schema_editor):
    """
    Create a TreatmentGroup row for every distinct (category, group-name)
    combination that exists in the old CharField, then point each Treatment
    at the new row.
    """
    Treatment = apps.get_model('treatments', 'Treatment')
    TreatmentGroup = apps.get_model('treatments', 'TreatmentGroup')

    seen = {}
    for treatment in Treatment.objects.filter(group_text__gt='').order_by('category_id', 'group_text'):
        key = (treatment.category_id, treatment.group_text)
        if key not in seen:
            tg = TreatmentGroup.objects.create(
                category_id=treatment.category_id,
                name=treatment.group_text,
                order=0,
            )
            seen[key] = tg.id
        treatment.group_fk_id = seen[key]
        treatment.save(update_fields=['group_fk_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('treatments', '0003_treatment_group_unique'),
    ]

    operations = [
        # 1. Create the TreatmentGroup table
        migrations.CreateModel(
            name='TreatmentGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('order', models.PositiveIntegerField(default=0, help_text='Controls display order within a category')),
                ('category', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='groups',
                    to='treatments.treatmentcategory',
                )),
            ],
            options={
                'ordering': ['category__order', 'order', 'name'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='treatmentgroup',
            unique_together={('category', 'name')},
        ),

        # 2. Rename old CharField so data migration can read it
        migrations.RenameField(
            model_name='treatment',
            old_name='group',
            new_name='group_text',
        ),

        # 3. Add nullable FK (temp name to avoid clash)
        migrations.AddField(
            model_name='treatment',
            name='group_fk',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='treatments',
                to='treatments.treatmentgroup',
                help_text="Optional subgroup within a category, e.g. 'Face', 'Body'. "
                          "Cards with the same group are displayed together under a heading.",
            ),
        ),

        # 4. Populate the FK from the old text field
        migrations.RunPython(populate_groups, migrations.RunPython.noop),

        # 5. Drop the old CharField
        migrations.RemoveField(
            model_name='treatment',
            name='group_text',
        ),

        # 6. Rename FK to 'group'
        migrations.RenameField(
            model_name='treatment',
            old_name='group_fk',
            new_name='group',
        ),
    ]
