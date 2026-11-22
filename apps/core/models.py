"""
Shared base models and singleton RestaurantSettings model.
Owned by Developer 1 (apps/core/).
"""
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Abstract base model that provides self-updating created_at and updated_at fields.
    Matches the TIMESTAMPTZ conventions in docs/schema.sql.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        return super().update(is_deleted=True, deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(is_deleted=False)

    def dead(self):
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class AllObjectsManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class SoftDeleteModel(TimeStampedModel):
    """
    Abstract base model supporting soft deletion (no hard deletes for immutable records).
    """

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])


class DeliveryFeeMode(models.TextChoices):
    FLAT = "FLAT", "Flat Rate"
    DISTANCE = "DISTANCE", "Distance Based"


class RestaurantSettings(TimeStampedModel):
    """
    Cached, admin-editable singleton settings model for restaurant origin,
    localization (Ghana & GHS), and delivery fee engine thresholds (Architecture §4.5).
    """

    CACHE_KEY = "core:restaurant_settings_singleton"

    restaurant_name = models.CharField(
        max_length=150,
        default="Cho Restaurant",
    )
    operating_country = models.CharField(
        max_length=100,
        default="Ghana",
    )
    currency = models.CharField(
        max_length=3,
        default="GHS",
    )
    currency_symbol = models.CharField(
        max_length=10,
        default="GH₵",
    )
    origin_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        default=Decimal("5.603717"),
        help_text="Restaurant latitude (Accra default: 5.603717).",
    )
    origin_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        default=Decimal("-0.186964"),
        help_text="Restaurant longitude (Accra default: -0.186964).",
    )
    delivery_fee_mode = models.CharField(
        max_length=20,
        choices=DeliveryFeeMode.choices,
        default=DeliveryFeeMode.DISTANCE,
    )
    flat_delivery_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("15.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    base_delivery_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("10.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    base_distance_km = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("3.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    per_km_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("3.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    max_delivery_radius_km = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("15.00"),
        validators=[MinValueValidator(Decimal("0.10"))],
    )
    free_delivery_threshold = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("200.00"),
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    is_ordering_open = models.BooleanField(default=True)

    class Meta:
        db_table = "core_restaurantsettings"
        verbose_name = "Restaurant Settings"
        verbose_name_plural = "Restaurant Settings"

    def __str__(self) -> str:
        return f"{self.restaurant_name} Settings ({self.operating_country} - {self.currency})"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete(self.CACHE_KEY)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def get_solo(cls) -> "RestaurantSettings":
        cached = cache.get(cls.CACHE_KEY)
        if cached is not None:
            return cached
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "restaurant_name": getattr(settings, "RESTAURANT_NAME", "Cho Restaurant"),
                "operating_country": getattr(settings, "DEFAULT_COUNTRY", "Ghana"),
                "currency": getattr(settings, "DEFAULT_CURRENCY", "GHS"),
                "currency_symbol": getattr(settings, "CURRENCY_SYMBOL", "GH₵"),
                "origin_latitude": getattr(settings, "RESTAURANT_LATITUDE", Decimal("5.603717")),
                "origin_longitude": getattr(settings, "RESTAURANT_LONGITUDE", Decimal("-0.186964")),
                "delivery_fee_mode": getattr(settings, "DELIVERY_FEE_MODE", DeliveryFeeMode.DISTANCE),
                "flat_delivery_fee": getattr(settings, "FLAT_DELIVERY_FEE", Decimal("15.00")),
                "base_delivery_fee": getattr(settings, "BASE_DELIVERY_FEE", Decimal("10.00")),
                "base_distance_km": getattr(settings, "BASE_DISTANCE_KM", Decimal("3.00")),
                "per_km_fee": getattr(settings, "PER_KM_FEE", Decimal("3.00")),
                "max_delivery_radius_km": getattr(settings, "MAX_DELIVERY_RADIUS_KM", Decimal("15.00")),
                "free_delivery_threshold": getattr(settings, "FREE_DELIVERY_THRESHOLD", Decimal("200.00")),
            },
        )
        cache.set(cls.CACHE_KEY, obj, timeout=300)
        return obj
