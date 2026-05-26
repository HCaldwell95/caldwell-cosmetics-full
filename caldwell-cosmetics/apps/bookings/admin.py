from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display  = ['date', 'start_time', 'treatment', 'user', 'status', 'created_at']
    list_filter   = ['status', 'date', 'treatment__category']
    search_fields = ['user__email', 'user__first_name', 'treatment__name']
    ordering      = ['date', 'start_time']
    date_hierarchy = 'date'