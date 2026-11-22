"""
DRF JSON API Views for Accounts, Authentication, Profiles, Addresses, and Riders.
Owned by Developer 1.
"""
from django.contrib.auth import login, logout
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdminRole, IsRider, IsStaffOrAdmin

from .models import Address, CustomerProfile, RiderProfile, User
from .serializers import (
    AddressSerializer,
    CustomerProfileSerializer,
    LoginSerializer,
    RegisterSerializer,
    RiderProfileSerializer,
    RoleUpdateSerializer,
    UserSerializer,
)
from .services import (
    authenticate_user,
    change_user_role,
    get_available_riders,
    set_default_address,
)


class RegisterAPIView(APIView):
    """POST /api/accounts/register/ — Register a new customer account."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user)
        return Response(
            {
                "message": "Registration successful.",
                "user": UserSerializer(user, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginAPIView(APIView):
    """POST /api/accounts/login/ — Authenticate with username or email."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data["resolved_identifier"]
        password = serializer.validated_data["password"]

        user = authenticate_user(request, identifier=identifier, password=password)
        if user is None:
            return Response(
                {"detail": "Invalid username/email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.is_active:
            return Response(
                {"detail": "This account is deactivated."},
                status=status.HTTP_403_FORBIDDEN,
            )

        login(request, user)
        return Response(
            {
                "message": "Login successful.",
                "user": UserSerializer(user, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class LogoutAPIView(APIView):
    """POST /api/accounts/logout/ — Log out the active session."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)


class ProfileAPIView(APIView):
    """
    GET / PATCH / PUT /api/accounts/profile/
    Retrieve or update the current user's account details and customer notification preferences.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user, context={"request": request}).data)

    def patch(self, request):
        user = request.user
        user_serializer = UserSerializer(
            user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        user_serializer.is_valid(raise_exception=True)
        user_serializer.save()

        # Also update customer notification preferences if provided
        if user.is_customer:
            profile, _ = CustomerProfile.objects.get_or_create(user=user)
            profile_fields = {
                k: request.data[k]
                for k in ("notify_email", "notify_sms", "default_address_id")
                if k in request.data
            }
            if profile_fields:
                prof_serializer = CustomerProfileSerializer(
                    profile,
                    data=profile_fields,
                    partial=True,
                    context={"request": request},
                )
                prof_serializer.is_valid(raise_exception=True)
                prof_serializer.save()

        user.refresh_from_db()
        return Response(UserSerializer(user, context={"request": request}).data)

    def put(self, request):
        return self.patch(request)


class AddressListCreateAPIView(generics.ListCreateAPIView):
    """
    GET / POST /api/accounts/addresses/
    List saved delivery addresses for the current user or create a new one.
    """

    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AddressDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET / PUT / PATCH / DELETE /api/accounts/addresses/<id>/
    Manage a specific delivery address owned by the current user.
    """

    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class SetDefaultAddressAPIView(APIView):
    """
    POST /api/accounts/addresses/<id>/set-default/
    Set the specified address as the user's default delivery address.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        try:
            address = set_default_address(request.user, pk)
        except DjangoValidationError as exc:
            return Response({"detail": str(exc.message)}, status=status.HTTP_404_NOT_FOUND)
        return Response(AddressSerializer(address).data, status=status.HTTP_200_OK)


class RiderProfileSelfAPIView(APIView):
    """
    GET / PATCH /api/accounts/rider-profile/
    Allows an authenticated RIDER to inspect and update their availability,
    vehicle info, and GPS sharing consent.
    """

    permission_classes = [IsAuthenticated, IsRider]

    def get(self, request):
        profile, _ = RiderProfile.objects.get_or_create(user=request.user)
        return Response(RiderProfileSerializer(profile).data)

    def patch(self, request):
        profile, _ = RiderProfile.objects.get_or_create(user=request.user)
        serializer = RiderProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class RiderListAPIView(generics.ListAPIView):
    """
    GET /api/accounts/riders/?available_only=true
    Staff/Admin endpoint to list dispatch riders (used by Developer 4 & 5 for assignment).
    """

    serializer_class = RiderProfileSerializer
    permission_classes = [IsAuthenticated, IsStaffOrAdmin]

    def get_queryset(self):
        available_only = self.request.query_params.get("available_only", "").lower() in (
            "1",
            "true",
            "yes",
        )
        if available_only:
            return get_available_riders()
        return RiderProfile.objects.select_related("user").all()


class UserListAPIView(generics.ListAPIView):
    """
    GET /api/accounts/users/?role=CUSTOMER
    Admin/Staff endpoint to list users with optional role filter.
    """

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsStaffOrAdmin]

    def get_queryset(self):
        qs = User.objects.all().order_by("-date_joined")
        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role=role.upper())
        return qs


class UserRoleUpdateAPIView(APIView):
    """
    PATCH /api/accounts/users/<id>/role/
    Admin-only endpoint to update a user's role or verify a rider profile.
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    def patch(self, request, pk: int):
        target_user = get_object_or_404(User, pk=pk)
        serializer = RoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_role = serializer.validated_data["role"]
        target_user = change_user_role(request.user, target_user, new_role)

        if "is_verified" in serializer.validated_data and target_user.is_rider:
            rider_profile, _ = RiderProfile.objects.get_or_create(user=target_user)
            rider_profile.is_verified = serializer.validated_data["is_verified"]
            rider_profile.save(update_fields=["is_verified", "updated_at"])
            target_user.rider_profile = rider_profile

        return Response(UserSerializer(target_user, context={"request": request}).data)
