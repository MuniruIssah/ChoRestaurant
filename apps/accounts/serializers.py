"""
DRF Serializers for Accounts, Profiles, Delivery Addresses, and Riders.
Provides documented data contracts for Developers 2, 3, 4, and 5.
Owned by Developer 1.
"""
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Address, CustomerProfile, RiderProfile, User, UserRole
from .services import register_user


class AddressSerializer(serializers.ModelSerializer):
    has_coordinates = serializers.BooleanField(read_only=True)

    class Meta:
        model = Address
        fields = (
            "id",
            "label",
            "line1",
            "line2",
            "city",
            "state",
            "postal_code",
            "country",
            "latitude",
            "longitude",
            "is_default",
            "has_coordinates",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "has_coordinates", "created_at", "updated_at")


class CustomerProfileSerializer(serializers.ModelSerializer):
    default_address = AddressSerializer(read_only=True)
    default_address_id = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.all(),
        source="default_address",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = CustomerProfile
        fields = (
            "id",
            "loyalty_points",
            "default_address",
            "default_address_id",
            "notify_in_app",
            "notify_email",
            "notify_sms",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "loyalty_points", "notify_in_app", "created_at", "updated_at")

    def validate_default_address_id(self, address):
        request = self.context.get("request")
        if address and request and address.user_id != request.user.id:
            raise serializers.ValidationError("Default address must belong to the current user.")
        return address


class RiderProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = RiderProfile
        fields = (
            "id",
            "user_id",
            "username",
            "email",
            "phone",
            "full_name",
            "vehicle_type",
            "plate_number",
            "is_available",
            "is_verified",
            "location_consent",
            "current_lat",
            "current_lng",
            "last_seen",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user_id",
            "username",
            "email",
            "phone",
            "full_name",
            "is_verified",
            "last_seen",
            "created_at",
            "updated_at",
        )

    def get_full_name(self, obj: RiderProfile) -> str:
        return obj.user.get_full_name() or obj.user.username


class UserSerializer(serializers.ModelSerializer):
    customer_profile = CustomerProfileSerializer(read_only=True)
    rider_profile = RiderProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "is_email_verified",
            "is_active",
            "date_joined",
            "customer_profile",
            "rider_profile",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "role",
            "is_email_verified",
            "is_active",
            "date_joined",
            "customer_profile",
            "rider_profile",
            "created_at",
            "updated_at",
        )


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, required=False)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")

    def validate_username(self, value: str) -> str:
        if User.objects.filter(username__iexact=value.strip()).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value.strip()

    def validate_email(self, value: str) -> str:
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate(self, attrs):
        password = attrs.get("password")
        password_confirm = attrs.get("password_confirm")
        if password_confirm is not None and password != password_confirm:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        validate_password(password)
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm", None)
        return register_user(role=UserRole.CUSTOMER, **validated_data)


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(
        help_text="Username or email address",
        required=False,
    )
    username = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        identifier = (
            attrs.get("identifier")
            or attrs.get("username")
            or attrs.get("email")
        )
        if not identifier:
            raise serializers.ValidationError(
                {"identifier": "Provide identifier, username, or email."}
            )
        attrs["resolved_identifier"] = identifier
        return attrs


class RoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=UserRole.choices)
    is_verified = serializers.BooleanField(required=False)


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True, required=False)

    def validate_old_password(self, value: str) -> str:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        new_password = attrs.get("new_password")
        new_password_confirm = attrs.get("new_password_confirm")
        if new_password_confirm is not None and new_password != new_password_confirm:
            raise serializers.ValidationError(
                {"new_password_confirm": "New passwords do not match."}
            )
        request = self.context.get("request")
        validate_password(new_password, user=getattr(request, "user", None))
        return attrs

