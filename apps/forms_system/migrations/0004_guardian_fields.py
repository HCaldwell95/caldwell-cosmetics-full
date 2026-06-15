from django.db import migrations, models

MODELS = [
    'consultationform',
    'botoxconsentform',
    'photographyconsent',
    'prpconsentform',
    'laserreconsent',
    'recordcard',
]

FIELDS = [
    ('guardian_name',         models.CharField(max_length=200, blank=True)),
    ('guardian_relationship', models.CharField(max_length=100, blank=True)),
    ('guardian_phone',        models.CharField(max_length=20,  blank=True)),
    ('guardian_email',        models.EmailField(blank=True)),
    ('guardian_signature',    models.TextField(blank=True)),
]


class Migration(migrations.Migration):

    dependencies = [
        ('forms_system', '0003_alter_prpconsentform_completed_by_practitioner_and_more'),
    ]

    operations = [
        migrations.AddField(model_name=model, name=name, field=field)
        for model in MODELS
        for name, field in FIELDS
    ]
