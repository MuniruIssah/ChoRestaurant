"""
Accounts domain models:
  - User (accounts_user)
  - CustomerProfile (accounts_customerprofile)
  - Address (accounts_address)
  - RiderProfile (accounts_riderprofile)
Matches docs/schema.sql with Ghana default country localization.
Owned by Developer 1. Boundary: Other developers must not independently modify User.
"""
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from apps.core.models import TimeStampedModel

from .managers import UserManager


class UserRole(models.TextChoices):
    CUSTOMER = "CUSTOMER", "Customer"
    STAFF = "STAFF", "Restaurant Staff"
    RIDER = "RIDER", "Dispatch Rider"
    ADMIN = "ADMIN", "Administrator"


class User(AbstractUser, TimeStampedModel):
    """
    Custom User model for the Restaurant Ordering & Delivery Management System.
    Created before the first database migration (AUTH_USER_MODEL = 'accounts.User').
    """

    email = models.EmailField("email address", max_length=254, unique=True, db_index=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CUSTOMER,
        db_index=True,
    )
    is_email_verified = models.BooleanField(default=False)

    objects = UserManager()

    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "accounts_user"
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=["role"], name="idx_user_role"),
            models.Index(fields=["email"], name="idx_user_email"),
        ]

    def __str__(self) -> str:
        return f"{self.username} ({self.get_role_display()})"

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.email.strip().lower()

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        if self.is_superuser or self.role == UserRole.ADMIN:
            self.is_staff = True
        super().save(*args, **kwargs)

    @property
    def is_customer(self) -> bool:
        return self.role == UserRole.CUSTOMER

    @property
    def is_restaurant_staff(self) -> bool:
        return self.role in (UserRole.STAFF, UserRole.ADMIN)

    @property
    def is_rider(self) -> bool:
        return self.role == UserRole.RIDER

    @property
    def is_admin_role(self) -> bool:
        return self.role == UserRole.ADMIN or self.is_superuser


class Address(TimeStampedModel):
    """
    Saved delivery addresses for customers (accounts_address).
    Includes GPS coordinates (latitude/longitude) and Ghana default country.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    label = models.CharField(max_length=50, default="Home")
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, help_text="Region or State (e.g., Greater Accra)")
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(
        max_length=100,
        default="Ghana",
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(Decimal("-90.000000")),
            MaxValueValidator(Decimal("90.000000")),
        ],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(Decimal("-180.000000")),
            MaxValueValidator(Decimal("180.000000")),
        ],
    )
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = "accounts_address"
        verbose_name = "Delivery Address"
        verbose_name_plural = "Delivery Addresses"
        ordering = ["-is_default", "-updated_at"]
        indexes = [
            models.Index(fields=["user"], name="idx_address_user"),
        ]

    def __str__(self) -> str:
        return f"{self.label}: {self.line1}, {self.city} ({self.country})"

    @property
    def has_coordinates(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    def save(self, *args, **kwargs):
        with transaction.atomic():
            existing_qs = Address.objects.filter(user=self.user)
            if self.pk:
                existing_qs = existing_qs.exclude(pk=self.pk)
            if not existing_qs.exists():
                self.is_default = True
            elif self.is_default:
                existing_qs.filter(is_default=True).update(is_default=False)

            super().save(*args, **kwargs)

            if self.is_default:
                CustomerProfile.objects.filter(user=self.user).update(default_address=self)


class CustomerProfile(TimeStampedModel):
    """
    Customer-specific profile data (accounts_customerprofile).
    One-to-one with a user; stores default delivery address, loyalty points,
    and notification preferences (PRD §4.1 & §4.9).
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )
    default_address = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    loyalty_points = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
    )
    # Notification preferences (PRD §4.9: users can opt out of email/SMS, in-app always enabled)
    notify_in_app = models.BooleanField(default=True)
    notify_email = models.BooleanField(default=True)
    notify_sms = models.BooleanField(default=False)

    class Meta:
        db_table = "accounts_customerprofile"
        verbose_name = "Customer Profile"
        verbose_name_plural = "Customer Profiles"

    def __str__(self) -> str:
        return f"CustomerProfile({self.user.username})"

    def clean(self):
        super().clean()
        if self.default_address and self.default_address.user_id != self.user_id:
            raise ValidationError("Default address must belong to the same user.")
        # PRD §4.9: Users must always receive in-app status notifications
        self.notify_in_app = True

    def save(self, *args, **kwargs):
        self.notify_in_app = True
        super().save(*args, **kwargs)


class VehicleType(models.TextChoices):
    MOTORCYCLE = "MOTORCYCLE", "Motorcycle"
    BICYCLE = "BICYCLE", "Bicycle"
    CAR = "CAR", "Car"
    VAN = "VAN", "Van"


class RiderProfile(TimeStampedModel):
    """
    Dispatch Rider profile model (accounts_riderprofile).
    Tracks vehicle info, availability, verification, GPS consent, and latest coordinates.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rider_profile",
    )
    vehicle_type = models.CharField(
        max_length=50,
        choices=VehicleType.choices,
        default=VehicleType.MOTORCYCLE,
    )
    plate_number = models.CharField(max_length=20, blank=True, null=True)
    is_available = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    location_consent = models.BooleanField(
        default=False,
        help_text="Whether the rider has enabled live GPS sharing during active deliveries.",
    )
    current_lat = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(Decimal("-90.000000")),
            MaxValueValidator(Decimal("90.000000")),
        ],
    )
    current_lng = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(Decimal("-180.000000")),
            MaxValueValidator(Decimal("180.000000")),
        ],
    )
    last_seen = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "accounts_riderprofile"
        verbose_name = "Rider Profile"
        verbose_name_plural = "Rider Profiles"
        indexes = [
            models.Index(fields=["is_available", "is_verified"], name="idx_rider_available"),
        ]

    def __str__(self) -> str:
        status = "Available" if self.is_available else "Busy/Offline"
        return f"RiderProfile({self.user.username} - {self.vehicle_type} - {status})"

    def update_location(self, latitude: Decimal | float, longitude: Decimal | float) -> None:
        """
        Update the rider's current GPS coordinates and last_seen timestamp.
        Requires location_consent=True per PRD §4.6.
        """
        if not self.location_consent:
            raise ValidationError("Rider has not granted GPS location sharing consent.")
        self.current_lat = Decimal(str(latitude))
        self.current_lng = Decimal(str(longitude))
        self.last_seen = timezone.now()
        self.save(update_fields=["current_lat", "current_lng", "last_seen", "updated_at"])

    def clear_location(self) -> None:
        """Clear last coordinates after delivery completion for rider privacy (PRD §4.6)."""
        self.current_lat = None
        self.current_lng = None
        self.save(update_fields=["current_lat", "current_lng", "updated_at"])
