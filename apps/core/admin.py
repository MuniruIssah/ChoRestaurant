from django.contrib import admin

from .models import RestaurantSettings


@admin.register(RestaurantSettings)
class RestaurantSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "restaurant_name",
        "operating_country",
        "currency",
        "delivery_fee_mode",
        "flat_delivery_fee",
        "base_delivery_fee",
        "max_delivery_radius_km",
        "is_ordering_open",
        "updated_at",
    )
    fieldsets = (
        (
            "General & Localization",
            {
                "fields": (
                    "restaurant_name",
                    "operating_country",
                    "currency",
                    "currency_symbol",
                    "is_ordering_open",
                )
            },
        ),
        (
            "Restaurant GPS Origin",
            {
                "fields": (
                    "origin_latitude",
                    "origin_longitude",
                )
            },
        ),
        (
            "Delivery Fee Configuration",
            {
                "fields": (
                    "delivery_fee_mode",
                    "flat_delivery_fee",
                    "base_delivery_fee",
                    "base_distance_km",
                    "per_km_fee",
                    "max_delivery_radius_km",
                    "free_delivery_threshold",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        if RestaurantSettings.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False
