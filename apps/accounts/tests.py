"""
Unit tests for apps.accounts covering authentication, profiles, delivery addresses,
validation, and security/IDOR edge cases.
Owned by Developer 1.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import Address, CustomerProfile, RiderProfile, User, UserRole
from apps.accounts.services import register_user, set_default_address


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

        # 5. Update profile & notification preferences (and verify notify_in_app stays True)
        prof_resp = self.client.patch(
            reverse("accounts-api:profile"),
            {
                "first_name": "Efua Nana",
                "notify_sms": True,
                "notify_in_app": False,
            },
            format="json",
        )
        self.assertEqual(prof_resp.status_code, 200)
        self.assertEqual(prof_resp.data["first_name"], "Efua Nana")
        self.assertTrue(prof_resp.data["customer_profile"]["notify_sms"])
        self.assertTrue(prof_resp.data["customer_profile"]["notify_in_app"])

    def test_registration_duplicate_and_password_mismatch_edge_cases(self):
        register_user(
            username="existing_user",
            email="existing@example.com",
            password="StrongPassword123!",
        )
        # Case-insensitive duplicate email
        dup_email_resp = self.client.post(
            reverse("accounts-api:register"),
            {
                "username": "brand_new",
                "email": "EXISTING@example.com",
                "password": "StrongPassword123!",
            },
            format="json",
        )
        self.assertEqual(dup_email_resp.status_code, 400)
        self.assertIn("email", dup_email_resp.data)

        # Case-insensitive duplicate username
        dup_user_resp = self.client.post(
            reverse("accounts-api:register"),
            {
                "username": "EXISTING_USER",
                "email": "unique@example.com",
                "password": "StrongPassword123!",
            },
            format="json",
        )
        self.assertEqual(dup_user_resp.status_code, 400)
        self.assertIn("username", dup_user_resp.data)

        # Mismatched password_confirm
        mismatch_resp = self.client.post(
            reverse("accounts-api:register"),
            {
                "username": "valid_user",
                "email": "valid@example.com",
                "password": "StrongPassword123!",
                "password_confirm": "DifferentPassword123!",
            },
            format="json",
        )
        self.assertEqual(mismatch_resp.status_code, 400)
        self.assertIn("password_confirm", mismatch_resp.data)

    def test_login_invalid_credentials_and_inactive_user_rejection(self):
        user = register_user(
            username="active_tester",
            email="tester@example.com",
            password="StrongPassword123!",
        )
        # Wrong password -> 401
        bad_pw_resp = self.client.post(
            reverse("accounts-api:login"),
            {"identifier": "tester@example.com", "password": "WrongPassword999!"},
            format="json",
        )
        self.assertEqual(bad_pw_resp.status_code, 401)

        # Deactivated user with right password -> 403
        user.is_active = False
        user.save(update_fields=["is_active"])
        inactive_resp = self.client.post(
            reverse("accounts-api:login"),
            {"identifier": "tester@example.com", "password": "StrongPassword123!"},
            format="json",
        )
        self.assertEqual(inactive_resp.status_code, 403)

    def test_cross_user_address_idor_protection_and_default_deletion_promotion(self):
        user_a = register_user(
            username="user_a", email="a@example.com", password="StrongPassword123!"
        )
        user_b = register_user(
            username="user_b", email="b@example.com", password="StrongPassword123!"
        )
        addr_a1 = Address.objects.create(
            user=user_a, label="Home A", line1="1 Street A", city="Accra", state="Greater Accra"
        )
        addr_a2 = Address.objects.create(
            user=user_a,
            label="Work A",
            line1="2 Street A",
            city="Accra",
            state="Greater Accra",
            is_default=True,
        )
        addr_b = Address.objects.create(
            user=user_b, label="Home B", line1="9 Street B", city="Accra", state="Greater Accra"
        )

        self.client.force_authenticate(user=user_a)

        # User A cannot view, edit, delete, or set-default on User B's address (returns 404)
        self.assertEqual(
            self.client.get(reverse("accounts-api:address-detail", kwargs={"pk": addr_b.pk})).status_code,
            404,
        )
        self.assertEqual(
            self.client.patch(
                reverse("accounts-api:address-detail", kwargs={"pk": addr_b.pk}),
                {"label": "Hacked"},
                format="json",
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.delete(
                reverse("accounts-api:address-detail", kwargs={"pk": addr_b.pk})
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                reverse("accounts-api:address-set-default", kwargs={"pk": addr_b.pk})
            ).status_code,
            404,
        )

        # User A cannot assign User B's address as their default_address_id on profile PATCH
        hijack_resp = self.client.patch(
            reverse("accounts-api:profile"),
            {"default_address_id": addr_b.pk},
            format="json",
        )
        self.assertEqual(hijack_resp.status_code, 400)

        # Deleting User A's current default address (addr_a2) via API promotes addr_a1 to default
        del_resp = self.client.delete(
            reverse("accounts-api:address-detail", kwargs={"pk": addr_a2.pk})
        )
        self.assertEqual(del_resp.status_code, 204)
        addr_a1.refresh_from_db()
        self.assertTrue(addr_a1.is_default)
        user_a.customer_profile.refresh_from_db()
        self.assertEqual(user_a.customer_profile.default_address_id, addr_a1.pk)

    def test_address_gps_coordinate_bounds_validation(self):
        user = register_user(
            username="gps_user", email="gps@example.com", password="StrongPassword123!"
        )
        self.client.force_authenticate(user=user)

        invalid_lat_resp = self.client.post(
            reverse("accounts-api:address-list"),
            {
                "label": "Bad Lat",
                "line1": "Somewhere",
                "city": "Accra",
                "state": "Greater Accra",
                "latitude": "95.123456",
                "longitude": "-0.180000",
            },
            format="json",
        )
        self.assertEqual(invalid_lat_resp.status_code, 400)
        self.assertIn("latitude", invalid_lat_resp.data)

        invalid_lng_resp = self.client.post(
            reverse("accounts-api:address-list"),
            {
                "label": "Bad Lng",
                "line1": "Somewhere",
                "city": "Accra",
                "state": "Greater Accra",
                "latitude": "5.600000",
                "longitude": "-195.000000",
            },
            format="json",
        )
        self.assertEqual(invalid_lng_resp.status_code, 400)
        self.assertIn("longitude", invalid_lng_resp.data)

    def test_password_change_and_rider_and_role_permissions_api(self):
        customer = register_user(
            username="regular_cust", email="reg@example.com", password="OldPassword123!"
        )
        rider = register_user(
            username="active_rider",
            email="rider_test@example.com",
            password="RiderPassword123!",
            role=UserRole.RIDER,
        )
        admin = User.objects.create_superuser(
            username="boss_admin", email="boss@example.com", password="AdminPassword123!"
        )

        # 1. Customer can change password with valid old_password, fails with wrong old_password
        self.client.force_authenticate(user=customer)
        bad_change = self.client.post(
            reverse("accounts-api:change-password"),
            {"old_password": "WrongOldPassword!", "new_password": "NewPassword456!"},
            format="json",
        )
        self.assertEqual(bad_change.status_code, 400)

        good_change = self.client.post(
            reverse("accounts-api:change-password"),
            {
                "old_password": "OldPassword123!",
                "new_password": "NewPassword456!",
                "new_password_confirm": "NewPassword456!",
            },
            format="json",
        )
        self.assertEqual(good_change.status_code, 200)
        customer.refresh_from_db()
        self.assertTrue(customer.check_password("NewPassword456!"))

        # 2. Customer cannot access rider-profile (403) or admin role-update endpoint (403)
        self.assertEqual(self.client.get(reverse("accounts-api:rider-profile")).status_code, 403)
        self.assertEqual(
            self.client.patch(
                reverse("accounts-api:user-role-update", kwargs={"pk": rider.pk}),
                {"role": "ADMIN"},
                format="json",
            ).status_code,
            403,
        )

        # 3. Rider can access and update their rider-profile (location_consent & plate_number)
        self.client.force_authenticate(user=rider)
        rider_resp = self.client.patch(
            reverse("accounts-api:rider-profile"),
            {"location_consent": True, "plate_number": "GW-999-26"},
            format="json",
        )
        self.assertEqual(rider_resp.status_code, 200)
        self.assertTrue(rider_resp.data["location_consent"])
        self.assertEqual(rider_resp.data["plate_number"], "GW-999-26")

        # 4. Admin can change user role and verify rider
        self.client.force_authenticate(user=admin)
        role_resp = self.client.patch(
            reverse("accounts-api:user-role-update", kwargs={"pk": customer.pk}),
            {"role": "RIDER", "is_verified": True},
            format="json",
        )
        self.assertEqual(role_resp.status_code, 200)
        self.assertEqual(role_resp.data["role"], "RIDER")
        self.assertTrue(role_resp.data["rider_profile"]["is_verified"])
        self.assertTrue(RiderProfile.objects.filter(user=customer, is_verified=True).exists())
