"""
Unit tests for apps.core (Shared models, SoftDeleteModel, permissions, RBAC mixins/decorators,
IsOwnerOrAdmin, maps facade, utilities, database/cloudinary URL parsers, and health check).
Owned by Developer 1.
"""
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.views import View

from apps.accounts.models import Address, User, UserRole
from apps.core.maps import MapsFacade
from apps.core.models import DeliveryFeeMode, RestaurantSettings
from apps.core.permissions import (
    AdminRequiredMixin,
    CustomerRequiredMixin,
    IsAdminRole,
    IsCustomer,
    IsOwnerOrAdmin,
    IsRider,
    IsStaff,
    ReadOnlyOrStaffAdmin,
    RiderRequiredMixin,
    StaffRequiredMixin,
    role_required,
    user_has_role,
)
from apps.core.utils import (
    api_response,
    format_currency,
    generate_unique_reference,
    haversine_distance_km,
    quantize_money,
)
from config.settings.base import parse_cloudinary_url, parse_database_url


class CoreUtilitiesAndConfigTests(TestCase):
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

        route_near = MapsFacade.evaluate_destination(5.573100, -0.196900)
        self.assertTrue(route_near.within_delivery_radius)
        self.assertGreater(route_near.distance_km, Decimal("0.00"))
        self.assertGreaterEqual(route_near.estimated_travel_minutes, 5)

        # Far destination (Kumasi: ~200 km from Accra) must be outside delivery radius
        route_far = MapsFacade.evaluate_destination(6.688500, -1.624400)
        self.assertFalse(route_far.within_delivery_radius)

    def test_parse_database_and_cloudinary_urls(self):
        pg_cfg = parse_database_url("postgres://cho_user:secret123@db.internal:5433/cho_prod")
        self.assertEqual(pg_cfg["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(pg_cfg["NAME"], "cho_prod")
        self.assertEqual(pg_cfg["USER"], "cho_user")
        self.assertEqual(pg_cfg["PASSWORD"], "secret123")
        self.assertEqual(pg_cfg["HOST"], "db.internal")
        self.assertEqual(pg_cfg["PORT"], "5433")

        sqlite_cfg = parse_database_url("sqlite:///test_local.sqlite3")
        self.assertEqual(sqlite_cfg["ENGINE"], "django.db.backends.sqlite3")
        self.assertTrue(sqlite_cfg["NAME"].endswith("test_local.sqlite3"))

        with self.assertRaises(ValueError):
            parse_database_url("mysql://user:pass@localhost/db")

        cloud_cfg = parse_cloudinary_url("cloudinary://123456789:my_secret_key@cho-cloud")
        self.assertEqual(cloud_cfg["CLOUD_NAME"], "cho-cloud")
        self.assertEqual(cloud_cfg["API_KEY"], "123456789")
        self.assertEqual(cloud_cfg["API_SECRET"], "my_secret_key")

        with self.assertRaises(ValueError):
            parse_cloudinary_url("http://invalid-scheme")

    def test_api_response_helper(self):
        resp = api_response(data={"item": 1}, message="Created", status_code=201)
        self.assertEqual(resp.status_code, 201)


class CorePermissionsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.customer = User.objects.create_user(
            username="cust1", email="cust1@example.com", password="Password123!", role=UserRole.CUSTOMER
        )
        self.other_customer = User.objects.create_user(
            username="cust2", email="cust2@example.com", password="Password123!", role=UserRole.CUSTOMER
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

        req_anon = self.factory.get("/staff-only/")
        req_anon.user = AnonymousUser()
        anon_resp = sample_staff_view(req_anon)
        self.assertEqual(anon_resp.status_code, 302)

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

    def test_drf_permission_classes_and_object_ownership(self):
        req = self.factory.get("/")

        req.user = self.customer
        self.assertTrue(IsCustomer().has_permission(req, None))
        self.assertFalse(IsStaff().has_permission(req, None))
        self.assertTrue(ReadOnlyOrStaffAdmin().has_permission(req, None))

        post_req = self.factory.post("/")
        post_req.user = self.customer
        self.assertFalse(ReadOnlyOrStaffAdmin().has_permission(post_req, None))

        req.user = self.staff
        self.assertTrue(IsStaff().has_permission(req, None))
        self.assertFalse(IsAdminRole().has_permission(req, None))
        post_req.user = self.staff
        self.assertTrue(ReadOnlyOrStaffAdmin().has_permission(post_req, None))

        req.user = self.rider
        self.assertTrue(IsRider().has_permission(req, None))

        req.user = self.admin
        self.assertTrue(IsAdminRole().has_permission(req, None))
        self.assertTrue(IsStaff().has_permission(req, None))

        # Object-level IsOwnerOrAdmin checks (for Address / Order ownership)
        addr = Address.objects.create(
            user=self.customer,
            label="Home",
            line1="10 Ring Road",
            city="Accra",
            state="Greater Accra",
        )
        mock_order = SimpleNamespace(customer=self.customer)
        owner_perm = IsOwnerOrAdmin()

        req.user = self.customer
        self.assertTrue(owner_perm.has_object_permission(req, None, addr))
        self.assertTrue(owner_perm.has_object_permission(req, None, mock_order))

        req.user = self.other_customer
        self.assertFalse(owner_perm.has_object_permission(req, None, addr))
        self.assertFalse(owner_perm.has_object_permission(req, None, mock_order))

        req.user = self.admin
        self.assertTrue(owner_perm.has_object_permission(req, None, addr))
        self.assertTrue(owner_perm.has_object_permission(req, None, mock_order))

    def test_health_check_and_home_portal_endpoints(self):
        response = self.client.get(reverse("health-check"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["country"], "Ghana")
        self.assertEqual(data["currency"], "GHS")
        self.assertTrue(data["database_connected"])
        self.assertIn("database_engine", data)
        self.assertIn("redis_configured", data)
        self.assertIn("media_storage_backend", data)

        home_resp = self.client.get(reverse("home"))
        self.assertEqual(home_resp.status_code, 200)
        self.assertContains(home_resp, "Cho Restaurant")
