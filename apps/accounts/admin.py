"""
Django Admin configuration for User, CustomerProfile, Address, and RiderProfile.
Owned by Developer 1.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Address, CustomerProfile, RiderProfile, User


class AddressInline(admin.TabularInline):
    model = Address
    extra = 0
    fields = ("label", "line1", "city", "state", "country", "latitude", "longitude", "is_default")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "phone",
        "is_email_verified",
        "is_active",
        "date_joined",
    )
    list_filter = ("role", "is_active", "is_staff", "is_superuser", "is_email_verified")
    search_fields = ("username", "email", "first_name", "last_name", "phone")
    ordering = ("-date_joined",)
    inlines = [AddressInline]

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Role & Contact Info",
            {
                "fields": (
                    "role",
                    "phone",
                    "is_email_verified",
                )
            },
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "Role & Contact Info",
            {
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "role",
                    "phone",
                )
            },
        ),
    )


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "default_address",
        "loyalty_points",
        "notify_in_app",
        "notify_email",
        "notify_sms",
        "updated_at",
    )
    search_fields = ("user__username", "user__email")
    list_filter = ("notify_email", "notify_sms")


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "label",
        "line1",
        "city",
        "state",
        "country",
        "is_default",
        "latitude",
        "longitude",
    )
    list_filter = ("country", "city", "state", "is_default")
    search_fields = ("user__username", "user__email", "line1", "city", "state")


@admin.register(RiderProfile)
class RiderProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "vehicle_type",
        "plate_number",
        "is_available",
        "is_verified",
        "location_consent",
        "current_lat",
        "current_lng",
        "last_seen",
    )
    readonly_fields = ("current_lat", "current_lng", "last_seen", "created_at", "updated_at")
    list_filter = ("vehicle_type", "is_available", "is_verified", "location_consent")
    search_fields = ("user__username", "user__email", "plate_number")
    actions = ["verify_riders", "mark_available", "mark_unavailable"]

    @admin.action(description="Verify selected dispatch riders")
    def verify_riders(self, request, queryset):
        queryset.update(is_verified=True)

    @admin.action(description="Mark selected riders as available")
    def mark_available(self, request, queryset):
        queryset.update(is_available=True)

    @admin.action(description="Mark selected riders as unavailable")
    def mark_unavailable(self, request, queryset):
        queryset.update(is_available=False)
