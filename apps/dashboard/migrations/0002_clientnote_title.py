from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="clientnote",
            name="title",
            field=models.CharField(default="", max_length=200),
            preserve_default=False,
        ),
    ]
