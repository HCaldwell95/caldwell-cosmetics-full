from datetime import date
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from cloudinary.models import CloudinaryField


# --------------------------------------------------
# CUSTOM USER MANAGER
# Makes email the login field instead of username
# --------------------------------------------------

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


# --------------------------------------------------
# USER MODEL
# Email is the unique identifier; username is unused
# --------------------------------------------------

class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True, verbose_name="Email address")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # email is already required by USERNAME_FIELD

    objects = UserManager()

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email


# --------------------------------------------------
# PROFILE MODEL
# Extended client data, auto-created via signal
# --------------------------------------------------

class SkinType(models.TextChoices):
    TYPE_1 = "type_1", "Type 1 – Always burns, never tans"
    TYPE_2 = "type_2", "Type 2 – Easily burns, eventually gets a moderate tan"
    TYPE_3 = "type_3", "Type 3 – Sometimes burns, quickly gets an average tan"
    TYPE_4 = "type_4", "Type 4 – Rarely burns, quickly gets a deep tan"
    TYPE_5 = "type_5", "Type 5 – Very rarely burns, consistent tan"
    TYPE_6 = "type_6", "Type 6 – Never burns, consistent tan"
    UNKNOWN = "unknown", "Unknown / Not assessed"


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    # Contact
    phone_number = models.CharField(max_length=20, blank=True)

    # Personal
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = CloudinaryField("profile_picture", blank=True, null=True)

    # Address
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    town_city      = models.CharField(max_length=100, blank=True)
    postcode       = models.CharField(max_length=10,  blank=True)

    # Skin
    skin_type = models.CharField(
        max_length=20,
        choices=SkinType.choices,
        default=SkinType.UNKNOWN,
    )

    # Medical — visible to staff only
    medical_notes = models.TextField(
        blank=True,
        help_text="For internal use only. Not visible to the client."
    )

    # Parent / Guardian (required for clients under 18)
    guardian_name         = models.CharField(max_length=150, blank=True)
    guardian_relationship = models.CharField(max_length=100, blank=True, help_text="e.g. Mother, Father, Guardian")
    guardian_phone        = models.CharField(max_length=20,  blank=True)
    guardian_email        = models.EmailField(blank=True)

    # GDPR
    gdpr_consent      = models.BooleanField(default=False)
    gdpr_consent_date = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"

    def __str__(self):
        return f"Profile — {self.user.full_name}"

    @property
    def age(self):
        """Returns the client's current age, or None if DOB not set."""
        if not self.date_of_birth:
            return None
        today = date.today()
        dob = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    @property
    def is_deactivated(self):
        return not self.user.is_active

    @property
    def is_minor(self):
        """True if the client is under 18, False if 18+, None if DOB not set."""
        age = self.age
        if age is None:
            return None
        return age < 18


# --------------------------------------------------
# SIGNAL
# Auto-creates a Profile whenever a new User is saved
# --------------------------------------------------

@receiver(post_save, sender=User)
def create_or_update_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        # Ensure a profile exists even if the signal was missed previously
        Profile.objects.get_or_create(user=instance)

# accounts/models.py

class PrepaidBundle(models.Model):
    """A block of pre-paid sessions for a specific treatment."""
    
    BUNDLE_STATUS = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bundles')
    treatment_name = models.CharField(max_length=200)
    total_sessions = models.PositiveIntegerField()          # e.g. 3 or 6
    sessions_used = models.PositiveIntegerField(default=0)
    date_purchased = models.DateField(auto_now_add=True)
    expiry_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=BUNDLE_STATUS, default='active')
    notes = models.TextField(blank=True)

    @property
    def sessions_remaining(self):
        return self.total_sessions - self.sessions_used

    @property
    def is_complete(self):
        return self.sessions_used >= self.total_sessions

    def __str__(self):
        return f"{self.user.full_name} — {self.treatment_name} ({self.sessions_remaining} remaining)"


class AccountCredit(models.Model):
    """A cash credit balance on the client's account."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='credit')
    balance = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.full_name} — £{self.balance}"


class CreditTransaction(models.Model):
    """Audit log of every credit change — additions and deductions."""

    TRANSACTION_TYPES = [
        ('credit', 'Credit Added'),
        ('deduct', 'Credit Deducted'),
        ('refund', 'Refund'),
    ]

    account = models.ForeignKey(AccountCredit, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)