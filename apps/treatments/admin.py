from django import forms
from django.contrib import admin
from django.utils.html import format_html
from .models import TreatmentCategory, TreatmentGroup, Treatment


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


class TreatmentGroupInline(admin.TabularInline):
    model = TreatmentGroup
    extra = 1
    fields = ["name", "order"]


class TreatmentInline(admin.TabularInline):
    model = Treatment
    extra = 1
    fields = [
        "name",
        "group",
        "duration_minutes",
        "price",
        "order",
        "is_active",
    ]
    show_change_link = True

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'group':
            parent_id = request.resolver_match.kwargs.get('object_id')
            if parent_id:
                kwargs['queryset'] = TreatmentGroup.objects.filter(category_id=parent_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(TreatmentCategory)
class TreatmentCategoryAdmin(admin.ModelAdmin):
    form = TreatmentCategoryAdminForm
    list_display = ["name", "colour_preview", "order", "is_active"]
    list_editable = ["order", "is_active"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["order"]
    inlines = [TreatmentGroupInline, TreatmentInline]

    def colour_preview(self, obj):
        return format_html(
            '<span style="display:inline-block;width:16px;height:16px;'
            'border-radius:50%;background:{};vertical-align:middle;'
            'margin-right:6px;border:1px solid rgba(0,0,0,0.15)"></span>{}',
            obj.colour, obj.colour,
        )
    colour_preview.short_description = 'Colour'


@admin.register(TreatmentGroup)
class TreatmentGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "order"]
    list_editable = ["order"]
    list_filter = ["category"]
    ordering = ["category__order", "order", "name"]


@admin.register(Treatment)
class TreatmentAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "group", "price", "order", "is_active"]
    list_editable = ["order", "is_active"]
    list_filter = ["category", "group", "is_active"]
    search_fields = ["name", "group__name"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["category__order", "group__order", "order"]
    fieldsets = [
        (None, {
            "fields": ["category", "name", "slug", "group", "summary"]
        }),
        ("Pricing & Duration", {
            "fields": ["price", "duration_minutes", "requires_deposit", "deposit_amount"]
        }),
        ("Display", {
            "fields": ["order", "is_active"]
        }),
    ]