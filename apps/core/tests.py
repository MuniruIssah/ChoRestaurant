"""
Unit tests for apps.core (Shared models, permissions, RBAC mixins/decorators, maps facade, utilities).
Owned by Developer 1.
"""
from decimal import Decimal

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.views import View

from apps.accounts.models import User, UserRole
from apps.core.maps import MapsFacade
from apps.core.models import DeliveryFeeMode, RestaurantSettings
from apps.core.permissions import (
    AdminRequiredMixin,
    CustomerRequiredMixin,
    IsAdminRole,
    IsCustomer,
    IsRider,
    IsStaff,
    RiderRequiredMixin,
    StaffRequiredMixin,
    role_required,
    user_has_role,
)
from apps.core.utils import (
    format_currency,
    generate_unique_reference,
    haversine_distance_km,
    quantize_money,
)


class CoreUtilitiesTests(TestCase):
    def test_quantize_money_and_format_currency(self):
        self.assertEqual(quantize_money("45.555"), Decimal("45.56"))
        self.assertEqual(quantize_money(10), Decimal("10.00"))
        self.assertEqual(format_currency("85.5", "GH₵"), "GH₵85.50")

    def test_generate_unique_reference_format(self):
        ref1 = generate_unique_reference("ORD")
        ref2 = generate_unique_reference("ORD")
        self.assertTrue(ref1.startswith("ORD-"))
        self.assertLessEqual(len(ref1), 24)
        self.assertNotEqual(ref1, ref2)

    def test_haversine_distance_km(self):
        # Distance between central Accra (5.6037, -0.1870) and Osu (5.5560, -0.1820) ~ 5.33 km
        dist = haversine_distance_km(5.6037, -0.1870, 5.5560, -0.1820)
        self.assertGreater(dist, Decimal("5.00"))
        self.assertLess(dist, Decimal("6.00"))

    def test_restaurant_settings_singleton_and_maps_facade(self):
        settings_obj = RestaurantSettings.get_solo()
        self.assertEqual(settings_obj.pk, 1)
        self.assertEqual(settings_obj.operating_country, "Ghana")
        self.assertEqual(settings_obj.currency, "GHS")
        self.assertEqual(settings_obj.delivery_fee_mode, DeliveryFeeMode.DISTANCE)

        route = MapsFacade.evaluate_destination(5.573100, -0.196900)
        self.assertTrue(route.within_delivery_radius)
        self.assertGreater(route.distance_km, Decimal("0.00"))
        self.assertGreaterEqual(route.estimated_travel_minutes, 5)


class CorePermissionsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.customer = User.objects.create_user(
            username="cust1", email="cust1@example.com", password="Password123!", role=UserRole.CUSTOMER
        )
        self.staff = User.objects.create_user(
            username="staff1", email="staff1@example.com", password="Password123!", role=UserRole.STAFF
        )
        self.rider = User.objects.create_user(
            username="rider1", email="rider1@example.com", password="Password123!", role=UserRole.RIDER
        )
        self.admin = User.objects.create_user(
            username="admin1", email="admin1@example.com", password="Password123!", role=UserRole.ADMIN
        )

    def test_user_has_role_helper(self):
        self.assertFalse(user_has_role(AnonymousUser(), "CUSTOMER"))
        self.assertTrue(user_has_role(self.customer, "customer"))
        self.assertFalse(user_has_role(self.customer, "STAFF"))
        self.assertTrue(user_has_role(self.staff, "STAFF", "ADMIN"))
        self.assertTrue(user_has_role(self.rider, "RIDER"))
        self.assertTrue(user_has_role(self.admin, "ADMIN"))

    def test_role_required_decorator(self):
        @role_required("STAFF", "ADMIN")
        def sample_staff_view(request):
            return HttpResponse("ok")

        req_customer = self.factory.get("/staff-only/")
        req_customer.user = self.customer
        with self.assertRaises(PermissionDenied):
            sample_staff_view(req_customer)

        req_staff = self.factory.get("/staff-only/")
        req_staff.user = self.staff
        response = sample_staff_view(req_staff)
        self.assertEqual(response.status_code, 200)

    def test_cbv_role_mixins(self):
        class StaffView(StaffRequiredMixin, View):
            def get(self, request):
                return HttpResponse("staff-ok")

        class CustomerView(CustomerRequiredMixin, View):
            def get(self, request):
                return HttpResponse("customer-ok")

        class RiderView(RiderRequiredMixin, View):
            def get(self, request):
                return HttpResponse("rider-ok")

        class AdminView(AdminRequiredMixin, View):
            def get(self, request):
                return HttpResponse("admin-ok")

        req = self.factory.get("/")
        req.user = self.customer
        self.assertEqual(CustomerView.as_view()(req).status_code, 200)
        with self.assertRaises(PermissionDenied):
            StaffView.as_view()(req)

        req.user = self.rider
        self.assertEqual(RiderView.as_view()(req).status_code, 200)

        req.user = self.admin
        self.assertEqual(AdminView.as_view()(req).status_code, 200)
        self.assertEqual(StaffView.as_view()(req).status_code, 200)

    def test_drf_permission_classes(self):
        req = self.factory.get("/")

        req.user = self.customer
        self.assertTrue(IsCustomer().has_permission(req, None))
        self.assertFalse(IsStaff().has_permission(req, None))

        req.user = self.staff
        self.assertTrue(IsStaff().has_permission(req, None))
        self.assertFalse(IsAdminRole().has_permission(req, None))

        req.user = self.rider
        self.assertTrue(IsRider().has_permission(req, None))

        req.user = self.admin
        self.assertTrue(IsAdminRole().has_permission(req, None))
        self.assertTrue(IsStaff().has_permission(req, None))

    def test_health_check_endpoint(self):
        response = self.client.get(reverse("health-check"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["country"], "Ghana")
        self.assertEqual(response.json()["currency"], "GHS")
        self.assertTrue(response.json()["database_connected"])
