"""
Django Admin configuration for Food Categories and Food Items.
Provides the menu administration backend required by Developer 1's tasks.
Owned by Developer 1.
"""
from django.contrib import admin

from .models import Category, FoodItem


class FoodItemInline(admin.TabularInline):
    model = FoodItem
    extra = 0
    fields = ("name", "slug", "price", "is_available", "is_featured", "prep_time_minutes")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "sort_order", "is_active", "created_at", "updated_at")
    list_editable = ("sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("sort_order", "name")
    inlines = [FoodItemInline]
    actions = ["activate_categories", "deactivate_categories"]

    @admin.action(description="Activate selected food categories")
    def activate_categories(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Deactivate selected food categories")
    def deactivate_categories(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "price",
        "formatted_price",
        "is_available",
        "is_featured",
        "prep_time_minutes",
        "updated_at",
    )
    list_editable = ("price", "is_available", "is_featured", "prep_time_minutes")
    list_filter = ("category", "is_available", "is_featured")
    search_fields = ("name", "slug", "description", "category__name")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("category__sort_order", "name")
    actions = [
        "mark_available",
        "mark_unavailable",
        "mark_featured",
        "unmark_featured",
    ]

    @admin.action(description="Mark selected food items as Available")
    def mark_available(self, request, queryset):
        queryset.update(is_available=True)

    @admin.action(description="Mark selected food items as Unavailable")
    def mark_unavailable(self, request, queryset):
        queryset.update(is_available=False)

    @admin.action(description="Mark selected food items as Featured (Special / Daily Offer)")
    def mark_featured(self, request, queryset):
        queryset.update(is_featured=True)

    @admin.action(description="Remove Featured status from selected food items")
    def unmark_featured(self, request, queryset):
        queryset.update(is_featured=False)
