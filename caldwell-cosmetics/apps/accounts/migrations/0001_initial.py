# apps/accounts/migrations/0001_initial.py

import cloudinary.models
import django.contrib.auth.models
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False, help_text="Designates that this user has all permissions without explicitly assigning them.", verbose_name="superuser status")),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                ("is_staff", models.BooleanField(default=False, help_text="Designates whether the user can log into this admin site.", verbose_name="staff status")),
                ("is_active", models.BooleanField(default=True, help_text="Designates whether this user should be treated as active.", verbose_name="active")),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now, verbose_name="date joined")),
                ("email", models.EmailField(max_length=254, unique=True, verbose_name="Email address")),
                ("groups", models.ManyToManyField(blank=True, related_name="user_set", related_query_name="user", to="auth.group", verbose_name="groups")),
                ("user_permissions", models.ManyToManyField(blank=True, related_name="user_set", related_query_name="user", to="auth.permission", verbose_name="user permissions")),
            ],
            options={
                "verbose_name": "User",
                "verbose_name_plural": "Users",
                "abstract": False,
            },
            managers=[
                ("objects", django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name="Profile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("phone_number", models.CharField(blank=True, max_length=20)),
                ("date_of_birth", models.DateField(blank=True, null=True)),
                ("profile_picture", cloudinary.models.CloudinaryField(blank=True, null=True, verbose_name="profile_picture")),
                ("address_line_1", models.CharField(blank=True, max_length=255)),
                ("address_line_2", models.CharField(blank=True, max_length=255)),
                ("town_city", models.CharField(blank=True, max_length=100)),
                ("postcode", models.CharField(blank=True, max_length=10)),
                ("skin_type", models.CharField(
                    choices=[
                        ("normal", "Normal"), ("dry", "Dry"), ("oily", "Oily"),
                        ("combination", "Combination"), ("sensitive", "Sensitive"),
                        ("unknown", "Unknown / Not assessed"),
                    ],
                    default="unknown",
                    max_length=20,
                )),
                ("medical_notes", models.TextField(blank=True, help_text="For internal use only. Not visible to the client.")),
                ("gdpr_consent", models.BooleanField(default=False)),
                ("gdpr_consent_date", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="profile",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "verbose_name": "Profile",
                "verbose_name_plural": "Profiles",
            },
        ),
    ]