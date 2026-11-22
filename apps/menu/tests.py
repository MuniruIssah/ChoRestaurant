"""
Unit tests for apps.menu (Category, FoodItem, slug generation, price quantization,
menu administration permissions, and availability toggles).
Owned by Developer 1.
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
from apps.menu.models import Category, FoodItem


class MenuModelAndAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            username="cust_menu",
            email="cust_menu@example.com",
            password="Password123!",
            role=UserRole.CUSTOMER,
        )
        self.staff = User.objects.create_user(
            username="staff_menu",
            email="staff_menu@example.com",
            password="Password123!",
            role=UserRole.STAFF,
        )
        self.category = Category.objects.create(
            name="Ghanaian Classics",
            description="Authentic local dishes",
            sort_order=1,
            is_active=True,
        )
        self.jollof = FoodItem.objects.create(
            category=self.category,
            name="Jollof Rice & Grilled Chicken",
            description="Smoky party jollof",
            price=Decimal("85.00"),
            is_available=True,
            is_featured=True,
            prep_time_minutes=25,
        )
        self.unavailable_item = FoodItem.objects.create(
            category=self.category,
            name="Sold Out Kontomire Stew",
            description="Out of stock today",
            price=Decimal("65.00"),
            is_available=False,
            is_featured=False,
        )

    def test_slug_generation_and_formatted_price(self):
        self.assertEqual(self.category.slug, "ghanaian-classics")
        self.assertEqual(self.jollof.slug, "jollof-rice-grilled-chicken")
        self.assertEqual(self.jollof.formatted_price, "GH₵85.00")
        self.assertTrue(self.jollof.is_orderable)
        self.assertFalse(self.unavailable_item.is_orderable)

    def test_public_menu_lists_only_available_items(self):
        resp = self.client.get(reverse("menu-api:fooditem-list"))
        self.assertEqual(resp.status_code, 200)
        results = resp.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["slug"], self.jollof.slug)

    def test_featured_items_endpoint(self):
        resp = self.client.get(reverse("menu-api:featured-items"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["name"], "Jollof Rice & Grilled Chicken")

    def test_customer_cannot_create_or_toggle_menu_items(self):
        self.client.force_authenticate(user=self.customer)
        create_resp = self.client.post(
            reverse("menu-api:category-list"),
            {"name": "Unauthorized Category"},
            format="json",
        )
        self.assertEqual(create_resp.status_code, 403)

        toggle_resp = self.client.post(
            reverse("menu-api:fooditem-toggle-availability", kwargs={"slug": self.jollof.slug})
        )
        self.assertEqual(toggle_resp.status_code, 403)

    def test_staff_can_create_food_items_and_toggle_availability(self):
        self.client.force_authenticate(user=self.staff)
        create_resp = self.client.post(
            reverse("menu-api:fooditem-list"),
            {
                "category": self.category.id,
                "name": "Fried Rice & Peppered Goat",
                "description": "Delicious spicy goat with fried rice",
                "price": "95.00",
                "is_available": True,
                "is_featured": False,
                "prep_time_minutes": 20,
            },
            format="json",
        )
        self.assertEqual(create_resp.status_code, 201)
        self.assertEqual(create_resp.data["formatted_price"], "GH₵95.00")

        toggle_resp = self.client.post(
            reverse("menu-api:fooditem-toggle-availability", kwargs={"slug": self.jollof.slug})
        )
        self.assertEqual(toggle_resp.status_code, 200)
        self.jollof.refresh_from_db()
        self.assertFalse(self.jollof.is_available)
