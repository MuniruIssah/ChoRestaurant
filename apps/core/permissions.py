"""
Role-Based Access Control (RBAC) mixins, view decorators, and DRF permission classes.
Architecture §3:
  - RoleRequiredMixin(allowed_roles=...) for class-based views.
  - @role_required("STAFF") decorator for function views.
  - DRF permission classes: IsCustomer, IsStaff, IsRider, IsAdminRole.
Owned by Developer 1.
"""
from functools import wraps
from typing import Iterable

from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission

ROLE_CUSTOMER = "CUSTOMER"
ROLE_STAFF = "STAFF"
ROLE_RIDER = "RIDER"
ROLE_ADMIN = "ADMIN"

ALL_ROLES = (ROLE_CUSTOMER, ROLE_STAFF, ROLE_RIDER, ROLE_ADMIN)


def normalize_roles(roles: Iterable[str] | str) -> set[str]:
    if isinstance(roles, str):
        return {roles.upper()}
    return {str(r).upper() for r in roles}


def user_has_role(user, *roles: str) -> bool:
    """
    Check if an authenticated user has one of the specified roles.
    Superusers and users with ADMIN role also satisfy admin checks.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    allowed = normalize_roles(roles)
    user_role = getattr(user, "role", "").upper()
    if getattr(user, "is_superuser", False) and ROLE_ADMIN in allowed:
        return True
    return user_role in allowed


# =============================================================================
# 1. Class-Based View Mixins
# =============================================================================
class RoleRequiredMixin(AccessMixin):
    """
    CBV mixin verifying that the current user is authenticated and has one of
    `allowed_roles` (or `role` single string attribute).
    """

    allowed_roles: Iterable[str] = ()
    role: str | None = None

    def get_allowed_roles(self) -> set[str]:
        if self.role:
            return normalize_roles([self.role, *self.allowed_roles])
        return normalize_roles(self.allowed_roles)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        allowed = self.get_allowed_roles()
        if allowed and not user_has_role(request.user, *allowed):
            raise PermissionDenied("You do not have permission to access this resource.")
        return super().dispatch(request, *args, **kwargs)


class CustomerRequiredMixin(RoleRequiredMixin):
    allowed_roles = (ROLE_CUSTOMER,)


class StaffRequiredMixin(RoleRequiredMixin):
    allowed_roles = (ROLE_STAFF, ROLE_ADMIN)


class RiderRequiredMixin(RoleRequiredMixin):
    allowed_roles = (ROLE_RIDER,)


class AdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = (ROLE_ADMIN,)


class StaffOrAdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = (ROLE_STAFF, ROLE_ADMIN)


# =============================================================================
# 2. Function-Based View Decorators
# =============================================================================
def role_required(*roles: str):
    """
    Decorator for function-based views restricting access to users with the given role(s).
    Accepts case-insensitive role names (e.g., @role_required("staff") or @role_required("STAFF", "ADMIN")).
    """
    allowed = normalize_roles(roles)

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login

                return redirect_to_login(request.get_full_path())
            if not user_has_role(request.user, *allowed):
                raise PermissionDenied("You do not have the required role to perform this action.")
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


customer_required = role_required(ROLE_CUSTOMER)
staff_required = role_required(ROLE_STAFF, ROLE_ADMIN)
rider_required = role_required(ROLE_RIDER)
admin_required = role_required(ROLE_ADMIN)
staff_or_admin_required = role_required(ROLE_STAFF, ROLE_ADMIN)


# =============================================================================
# 3. Django REST Framework Permission Classes
# =============================================================================
class IsCustomer(BasePermission):
    """Allows access only to users with CUSTOMER role."""

    message = "Customer role required."

    def has_permission(self, request, view) -> bool:
        return user_has_role(request.user, ROLE_CUSTOMER)


class IsStaff(BasePermission):
    """Allows access to restaurant STAFF (and ADMIN)."""

    message = "Restaurant staff role required."

    def has_permission(self, request, view) -> bool:
        return user_has_role(request.user, ROLE_STAFF, ROLE_ADMIN)


class IsRider(BasePermission):
    """Allows access only to users with RIDER role."""

    message = "Dispatch rider role required."

    def has_permission(self, request, view) -> bool:
        return user_has_role(request.user, ROLE_RIDER)


class IsAdminRole(BasePermission):
    """Allows access only to users with ADMIN role or Django superuser."""

    message = "Administrator role required."

    def has_permission(self, request, view) -> bool:
        return user_has_role(request.user, ROLE_ADMIN)


class IsStaffOrAdmin(BasePermission):
    """Allows access to users with STAFF or ADMIN role."""

    message = "Staff or Administrator role required."

    def has_permission(self, request, view) -> bool:
        return user_has_role(request.user, ROLE_STAFF, ROLE_ADMIN)


class IsOwnerOrAdmin(BasePermission):
    """Object-level permission allowing owners of an object or ADMIN users."""

    message = "You must be the owner of this record or an administrator."

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj) -> bool:
        if user_has_role(request.user, ROLE_ADMIN):
            return True
        owner = getattr(obj, "user", None) or getattr(obj, "customer", None)
        if owner is not None:
            return owner == request.user
        return obj == request.user


class ReadOnlyOrStaffAdmin(BasePermission):
    """Allows read-only access to anyone, and write access to STAFF or ADMIN."""

    message = "Write operations require Staff or Administrator permissions."

    def has_permission(self, request, view) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return user_has_role(request.user, ROLE_STAFF, ROLE_ADMIN)
