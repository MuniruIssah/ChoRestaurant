"""
Unit tests for apps.accounts (Custom User model, roles, automatic profiles, delivery addresses,
registration/login/logout/profile/rider APIs).
Owned by Developer 1.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import Address, CustomerProfile, RiderProfile, User, UserRole
from apps.accounts.services import change_user_role, register_user, set_default_address


class AccountsModelAndServiceTests(TestCase):
    def test_customer_creation_provisions_customer_profile(self):
        user = register_user(
            username="akua",
            email="Akua@Example.com",
            password="SecurePassword123!",
            first_name="Akua",
            last_name="Asante",
            phone="+233240001111",
            role=UserRole.CUSTOMER,
        )
        self.assertEqual(user.email, "akua@example.com")
        self.assertTrue(user.is_customer)
        self.assertFalse(user.is_staff)
        self.assertTrue(CustomerProfile.objects.filter(user=user).exists())
        self.assertTrue(user.customer_profile.notify_in_app)

    def test_rider_creation_provisions_rider_profile_and_enforces_gps_consent(self):
        rider_user = register_user(
            username="kofi_rider",
            email="kofi@example.com",
            password="SecurePassword123!",
            role=UserRole.RIDER,
            vehicle_type="MOTORCYCLE",
            plate_number="GR-100-26",
        )
        self.assertTrue(rider_user.is_rider)
        profile = rider_user.rider_profile
        self.assertEqual(profile.plate_number, "GR-100-26")
        self.assertFalse(profile.location_consent)

        # Updating location without consent must raise ValidationError (PRD §4.6)
        with self.assertRaises(ValidationError):
            profile.update_location(5.6037, -0.1870)

        # Grant consent and update location
        profile.location_consent = True
        profile.save()
        profile.update_location(5.6037, -0.1870)
        profile.refresh_from_db()
        self.assertEqual(profile.current_lat, Decimal("5.603700"))
        self.assertEqual(profile.current_lng, Decimal("-0.187000"))
        self.assertIsNotNone(profile.last_seen)

        # Clear location on delivery completion
        profile.clear_location()
        self.assertIsNone(profile.current_lat)
        self.assertIsNone(profile.current_lng)

    def test_address_default_sync_and_ghana_default_country(self):
        user = register_user(
            username="kwesi",
            email="kwesi@example.com",
            password="SecurePassword123!",
        )
        addr1 = Address.objects.create(
            user=user,
            label="Home",
            line1="10 Liberation Road",
            city="Accra",
            state="Greater Accra",
        )
        # First address automatically becomes default and defaults to Ghana
        self.assertTrue(addr1.is_default)
        self.assertEqual(addr1.country, "Ghana")
        user.customer_profile.refresh_from_db()
        self.assertEqual(user.customer_profile.default_address_id, addr1.id)

        addr2 = Address.objects.create(
            user=user,
            label="Office",
            line1="25 Osu Oxford Street",
            city="Accra",
            state="Greater Accra",
            is_default=True,
        )
        addr1.refresh_from_db()
        self.assertFalse(addr1.is_default)
        self.assertTrue(addr2.is_default)
        user.customer_profile.refresh_from_db()
        self.assertEqual(user.customer_profile.default_address_id, addr2.id)

        # Switch back to addr1 via service
        set_default_address(user, addr1.id)
        addr1.refresh_from_db()
        addr2.refresh_from_db()
        self.assertTrue(addr1.is_default)
        self.assertFalse(addr2.is_default)


class AccountsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_login_profile_and_address_api_workflow(self):
        # 1. Register via API
        reg_resp = self.client.post(
            reverse("accounts-api:register"),
            {
                "username": "efua_customer",
                "email": "efua@example.com",
                "password": "StrongPassword123!",
                "password_confirm": "StrongPassword123!",
                "first_name": "Efua",
                "last_name": "Mensah",
                "phone": "+233201234567",
            },
            format="json",
        )
        self.assertEqual(reg_resp.status_code, 201)
        self.assertEqual(reg_resp.data["user"]["role"], "CUSTOMER")

        # 2. Logout
        logout_resp = self.client.post(reverse("accounts-api:logout"))
        self.assertEqual(logout_resp.status_code, 200)

        # 3. Login using email address
        login_resp = self.client.post(
            reverse("accounts-api:login"),
            {
                "identifier": "efua@example.com",
                "password": "StrongPassword123!",
            },
            format="json",
        )
        self.assertEqual(login_resp.status_code, 200)
        self.assertEqual(login_resp.data["user"]["username"], "efua_customer")

        # 4. Create delivery address
        addr_resp = self.client.post(
            reverse("accounts-api:address-list"),
            {
                "label": "Home",
                "line1": "East Legon Boundary Road",
                "city": "Accra",
                "state": "Greater Accra",
                "latitude": "5.635000",
                "longitude": "-0.155000",
            },
            format="json",
        )
        self.assertEqual(addr_resp.status_code, 201)
        self.assertEqual(addr_resp.data["country"], "Ghana")
        self.assertTrue(addr_resp.data["is_default"])
        self.assertTrue(addr_resp.data["has_coordinates"])

        # 5. Update profile & notification preferences
        prof_resp = self.client.patch(
            reverse("accounts-api:profile"),
            {
                "first_name": "Efua Nana",
                "notify_sms": True,
            },
            format="json",
        )
        self.assertEqual(prof_resp.status_code, 200)
        self.assertEqual(prof_resp.data["first_name"], "Efua Nana")
        self.assertTrue(prof_resp.data["customer_profile"]["notify_sms"])

    def test_admin_can_change_user_role_and_verify_rider(self):
        admin = User.objects.create_superuser(
            username="boss_admin", email="boss@example.com", password="AdminPassword123!"
        )
        target = register_user(
            username="new_hire", email="hire@example.com", password="UserPassword123!"
        )
        self.client.force_authenticate(user=admin)

        resp = self.client.patch(
            reverse("accounts-api:user-role-update", kwargs={"pk": target.pk}),
            {"role": "RIDER", "is_verified": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["role"], "RIDER")
        self.assertTrue(resp.data["rider_profile"]["is_verified"])
        self.assertTrue(RiderProfile.objects.filter(user=target, is_verified=True).exists())
