from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('treatments', '0002_treatmentcategory_colour'),
    ]

    operations = [
        # 1. Add the group field
        migrations.AddField(
            model_name='treatment',
            name='group',
            field=models.CharField(
                blank=True,
                default='',
                help_text="Optional subgroup within a category, e.g. 'Face', 'Body', 'Packages'. Cards with the same group are displayed together under a heading.",
                max_length=100,
            ),
        ),

        # 2. Remove the old global unique constraint on slug
        migrations.AlterField(
            model_name='treatment',
            name='slug',
            field=models.SlugField(blank=True),
        ),

        # 3. Add unique_together so (name, category) must be unique
        #    — this is what allows "Chest" in two different categories
        migrations.AlterUniqueTogether(
            name='treatment',
            unique_together={('name', 'category')},
        ),
    ]