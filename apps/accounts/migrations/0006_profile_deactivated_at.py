from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_profile_guardian_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='deactivated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
