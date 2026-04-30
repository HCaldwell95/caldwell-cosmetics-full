# apps/accounts/forms.py

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
    gdpr_consent = forms.BooleanField(
        required=True,
        label="I agree to the storage and processing of my personal data in accordance with the Privacy Policy.",
    )

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "password1", "password2")

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