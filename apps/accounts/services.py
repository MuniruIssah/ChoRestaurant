"""
Account and authentication domain services.
Provides clean service interfaces for registration, login (username or email),
address management, rider availability, and role management.
Owned by Developer 1.
"""
from decimal import Decimal

from django.contrib.auth import authenticate
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .models import Address, CustomerProfile, RiderProfile, User, UserRole


@transaction.atomic
def register_user(
    *,
    username: str,
    email: str,
    password: str,
    first_name: str = "",
    last_name: str = "",
    phone: str = "",
    role: str = UserRole.CUSTOMER,
    vehicle_type: str = "MOTORCYCLE",
    plate_number: str = "",
) -> User:
    """
    Register a new user and provision their role-specific profile.
    """
    normalized_email = email.strip().lower()
    if User.objects.filter(email__iexact=normalized_email).exists():
        raise ValidationError({"email": "A user with this email already exists."})
    if User.objects.filter(username__iexact=username.strip()).exists():
        raise ValidationError({"username": "A user with this username already exists."})

    user = User.objects.create_user(
        username=username.strip(),
        email=normalized_email,
        password=password,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        phone=phone.strip() if phone else None,
        role=role,
    )

    if role == UserRole.CUSTOMER:
        cust_profile, _ = CustomerProfile.objects.get_or_create(user=user)
        user.customer_profile = cust_profile
    elif role == UserRole.RIDER:
        profile, _ = RiderProfile.objects.get_or_create(user=user)
        if vehicle_type or plate_number:
            profile.vehicle_type = vehicle_type or profile.vehicle_type
            profile.plate_number = plate_number or profile.plate_number
            profile.save(update_fields=["vehicle_type", "plate_number", "updated_at"])
        user.rider_profile = profile

    return user


def authenticate_user(request, identifier: str, password: str) -> User | None:
    """
    Authenticate a user by either their username or email address.
    If the user exists and the password matches, returns the User instance even if
    is_active=False so callers (LoginAPIView / login form) can distinguish inactive
    accounts (403) from bad credentials (401).
    """
    identifier = (identifier or "").strip()
    if not identifier or not password:
        return None

    user_obj = None
    if "@" in identifier:
        user_obj = User.objects.filter(email__iexact=identifier).first()
    else:
        user_obj = User.objects.filter(username__iexact=identifier).first()

    username = user_obj.username if user_obj else identifier
    authenticated = authenticate(request=request, username=username, password=password)
    if authenticated is not None:
        return authenticated

    if user_obj is not None and not user_obj.is_active and user_obj.check_password(password):
        return user_obj

    return None


@transaction.atomic
def set_default_address(user: User, address_id: int) -> Address:
    """
    Mark one of the user's saved addresses as their default delivery address
    and update their CustomerProfile.default_address.
    """
    try:
        address = Address.objects.get(pk=address_id, user=user)
    except Address.DoesNotExist as exc:
        raise ValidationError("Address not found for this user.") from exc

    Address.objects.filter(user=user, is_default=True).exclude(pk=address.pk).update(
        is_default=False
    )
    if not address.is_default:
        address.is_default = True
        address.save(update_fields=["is_default", "updated_at"])

    CustomerProfile.objects.filter(user=user).update(default_address=address)
    return address


def get_available_riders():
    """
    Return active, available, and verified RiderProfile records for dispatch assignment
    (consumed by Developer 4 and Developer 5).
    """
    return RiderProfile.objects.select_related("user").filter(
        user__is_active=True,
        is_available=True,
        is_verified=True,
    )


def update_rider_gps(
    user: User,
    latitude: Decimal | float,
    longitude: Decimal | float,
) -> RiderProfile:
    """
    Update a rider's current GPS position if they have granted location_consent.
    """
    if not user.is_rider:
        raise PermissionDenied("Only dispatch riders can update rider GPS coordinates.")
    profile, _ = RiderProfile.objects.get_or_create(user=user)
    profile.update_location(latitude=latitude, longitude=longitude)
    return profile


@transaction.atomic
def change_user_role(actor: User, target_user: User, new_role: str) -> User:
    """
    Allow an ADMIN user to change a user's role and provision any required profile.
    """
    if not actor.is_admin_role:
        raise PermissionDenied("Only administrators can modify user roles.")
    if new_role not in UserRole.values:
        raise ValidationError({"role": f"Invalid role: {new_role}"})

    target_user.role = new_role
    target_user.save(update_fields=["role", "is_staff", "updated_at"])

    if new_role == UserRole.CUSTOMER:
        CustomerProfile.objects.get_or_create(user=target_user)
    elif new_role == UserRole.RIDER:
        RiderProfile.objects.get_or_create(user=target_user)

    return target_user
