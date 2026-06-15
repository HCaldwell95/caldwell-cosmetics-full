from django.contrib import admin
from .models import PhotographyConsent


@admin.register(PhotographyConsent)
class PhotographyConsentAdmin(admin.ModelAdmin):
    list_display  = ["user", "completed_at", "completed_by_practitioner"]
    list_filter   = ["completed_by_practitioner"]
    search_fields = ["user__email", "user__first_name", "user__last_name"]
    readonly_fields = [
        "user", "completed_at", "completed_by_practitioner", "practitioner",
        "signature", "full_name", "date_of_birth", "address",
        "consent_1", "consent_2", "consent_3", "consent_4", "consent_5",
    ]
    ordering = ["-completed_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
