from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Profile, User, PrepaidBundle, AccountCredit, CreditTransaction


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Profile"
    fields = (
        "phone_number", "date_of_birth", "profile_picture",
        "address_line_1", "address_line_2", "town_city", "postcode",
        "skin_type", "medical_notes",
        "gdpr_consent", "gdpr_consent_date",
    )
    readonly_fields = ("gdpr_consent_date",)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_active")
    search_fields = ("email", "first_name", "last_name")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "password1", "password2"),
        }),
    )

    inlines = (ProfileInline,)

# accounts/admin.py

@admin.register(PrepaidBundle)
class PrepaidBundleAdmin(admin.ModelAdmin):
    list_display = ['user', 'treatment_name', 'sessions_remaining', 'total_sessions', 'status', 'date_purchased']
    list_filter = ['status', 'treatment_name']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'treatment_name']
    actions = ['mark_one_session_used']

    def mark_one_session_used(self, request, queryset):
        for bundle in queryset:
            if not bundle.is_complete:
                bundle.sessions_used += 1
                if bundle.is_complete:
                    bundle.status = 'completed'
                bundle.save()
        self.message_user(request, "Session(s) marked as used.")
    mark_one_session_used.short_description = "Mark one session as used"