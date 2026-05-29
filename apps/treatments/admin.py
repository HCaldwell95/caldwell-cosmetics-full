from django import forms
from django.contrib import admin
from django.utils.html import format_html
from .models import TreatmentCategory, Treatment


class TreatmentCategoryAdminForm(forms.ModelForm):
    class Meta:
        model = TreatmentCategory
        fields = '__all__'
        widgets = {
            'colour': forms.TextInput(attrs={
                'type': 'color',
                'style': 'width:60px;height:36px;padding:2px;cursor:pointer;',
            }),
        }


class TreatmentInline(admin.TabularInline):
    model = Treatment
    extra = 1
    fields = [
        "name",
        "duration_minutes",
        "price",
        "order",
        "is_active",
    ]
    show_change_link = True


@admin.register(TreatmentCategory)
class TreatmentCategoryAdmin(admin.ModelAdmin):
    form = TreatmentCategoryAdminForm
    list_display = ["name", "colour_preview", "order", "is_active"]
    list_editable = ["order", "is_active"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["order"]
    inlines = [TreatmentInline]

    def colour_preview(self, obj):
        return format_html(
            '<span style="display:inline-block;width:16px;height:16px;'
            'border-radius:50%;background:{};vertical-align:middle;'
            'margin-right:6px;border:1px solid rgba(0,0,0,0.15)"></span>{}',
            obj.colour, obj.colour,
        )
    colour_preview.short_description = 'Colour'


@admin.register(Treatment)
class TreatmentAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "price", "order", "is_active"]
    list_editable = ["order", "is_active"]
    list_filter = ["category", "is_active"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["category__order", "order"]