# apps/accounts/forms.py

from datetime import date

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils import timezone

from .models import User, Profile


# --------------------------------------------------
# REGISTRATION FORM
# --------------------------------------------------

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"placeholder": "Email address"}),
    )
    first_name = forms.CharField(
        required=True,
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "First name"}),
    )
    last_name = forms.CharField(
        required=True,
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Last name"}),
    )
    phone_number = forms.CharField(
        required=True,
        max_length=20,
        widget=forms.TextInput(attrs={"placeholder": "e.g. 07700 900000", "type": "tel"}),
        label="Mobile number",
    )
    date_of_birth = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Date of birth",
    )
    # Guardian fields — shown and required only when client is under 18
    guardian_name = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Full name"}),
        label="Parent / guardian name",
    )
    guardian_relationship = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Mother, Father, Guardian"}),
        label="Relationship to client",
    )
    guardian_phone = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={"placeholder": "e.g. 07700 900000", "type": "tel"}),
        label="Parent / guardian mobile",
    )
    guardian_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={"placeholder": "Email address (optional)"}),
        label="Parent / guardian email",
    )

    gdpr_consent = forms.BooleanField(
        required=True,
        label="I agree to the storage and processing of my personal data in accordance with the Privacy Policy.",
    )

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "password1", "password2")

    def _is_minor(self):
        dob = self.cleaned_data.get("date_of_birth")
        if not dob:
            return False
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return age < 18

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get("date_of_birth")
        if dob and dob >= date.today():
            raise forms.ValidationError("Please enter a valid date of birth.")
        return dob

    def clean(self):
        cleaned = super().clean()
        if self._is_minor():
            if not cleaned.get("guardian_name"):
                self.add_error("guardian_name", "Parent / guardian name is required for clients under 18.")
            if not cleaned.get("guardian_phone"):
                self.add_error("guardian_phone", "Parent / guardian mobile is required for clients under 18.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
            profile = user.profile
            profile.gdpr_consent = True
            profile.gdpr_consent_date = timezone.now()
            profile.phone_number = self.cleaned_data["phone_number"]
            profile.date_of_birth = self.cleaned_data["date_of_birth"]
            profile.guardian_name         = self.cleaned_data.get("guardian_name", "")
            profile.guardian_relationship = self.cleaned_data.get("guardian_relationship", "")
            profile.guardian_phone        = self.cleaned_data.get("guardian_phone", "")
            profile.guardian_email        = self.cleaned_data.get("guardian_email", "")
            profile.save()
        return user


# --------------------------------------------------
# LOGIN FORM
# --------------------------------------------------

class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "Email address", "autofocus": True}),
        label="Email address",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Password"}),
        label="Password",
    )


# --------------------------------------------------
# CLIENT PROFILE EDIT FORM
# --------------------------------------------------

class ProfileEditForm(forms.ModelForm):
    first_name = forms.CharField(
        required=True,
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "First name"}),
    )
    last_name = forms.CharField(
        required=True,
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Last name"}),
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"placeholder": "Email address"}),
    )

    class Meta:
        model = Profile
        fields = (
            "phone_number",
            "date_of_birth",
            "profile_picture",
            "address_line_1",
            "address_line_2",
            "town_city",
            "postcode",
            "skin_type",
        )
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "phone_number":   forms.TextInput(attrs={"placeholder": "Phone number"}),
            "address_line_1": forms.TextInput(attrs={"placeholder": "Address line 1"}),
            "address_line_2": forms.TextInput(attrs={"placeholder": "Address line 2"}),
            "town_city":      forms.TextInput(attrs={"placeholder": "Town or city"}),
            "postcode":       forms.TextInput(attrs={"placeholder": "Postcode"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields["first_name"].initial = self.user.first_name
            self.fields["last_name"].initial  = self.user.last_name
            self.fields["email"].initial      = self.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            self.user.first_name = self.cleaned_data["first_name"]
            self.user.last_name  = self.cleaned_data["last_name"]
            self.user.email      = self.cleaned_data["email"]
            if commit:
                self.user.save()
        if commit:
            profile.save()
        return profile


# --------------------------------------------------
# STAFF PROFILE EDIT FORM
# Extends client form to expose medical_notes
# --------------------------------------------------

class StaffProfileEditForm(ProfileEditForm):
    class Meta(ProfileEditForm.Meta):
        fields = ProfileEditForm.Meta.fields + ("medical_notes",)
        widgets = {
            **ProfileEditForm.Meta.widgets,
            "medical_notes": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": "Internal notes — not visible to the client.",
            }),
        }