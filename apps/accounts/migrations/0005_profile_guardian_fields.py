from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_alter_profile_skin_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='guardian_name',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='profile',
            name='guardian_relationship',
            field=models.CharField(blank=True, help_text='e.g. Mother, Father, Guardian', max_length=100),
        ),
        migrations.AddField(
            model_name='profile',
            name='guardian_phone',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='profile',
            name='guardian_email',
            field=models.EmailField(blank=True, max_length=254),
        ),
    ]
