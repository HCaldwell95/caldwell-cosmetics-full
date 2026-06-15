from django.contrib import admin
from .models import ClientNote


@admin.register(ClientNote)
class ClientNoteAdmin(admin.ModelAdmin):
    list_display  = ["number", "user", "author", "created_at"]
    list_filter   = ["author"]
    search_fields = ["user__email", "user__first_name", "user__last_name", "content"]
    readonly_fields = ["number", "user", "author", "created_at", "content"]
    ordering      = ["-created_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
