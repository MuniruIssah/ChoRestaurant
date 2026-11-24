"""
Unit tests for apps.orders Phase 1 (Cart, CartItem, Order, OrderItem price/address snapshots,
unique reference generation, and OrderStatusHistory immutability).
Owned by Developer 3.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.models import Address, User, UserRole
from apps.menu.models import Category, FoodItem
from apps.orders.models import (
    Cart,
    CartItem,
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusHistory,
    PaymentMethod,
)


class OrdersPhase1ModelTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username="order_cust",
            email="order_cust@example.com",
            password="Password123!",
            role=UserRole.CUSTOMER,
        )
        self.staff = User.objects.create_user(
            username="order_staff",
            email="order_staff@example.com",
            password="Password123!",
            role=UserRole.STAFF,
        )
        self.address = Address.objects.create(
            user=self.customer,
            label="Home",
            line1="15 Cantonments Road",
            city="Accra",
            state="Greater Accra",
            latitude=Decimal("5.580000"),
            longitude=Decimal("-0.170000"),
        )
        self.category = Category.objects.create(name="Mains", sort_order=1, is_active=True)
        self.jollof = FoodItem.objects.create(
            category=self.category,
            name="Special Jollof",
            price=Decimal("80.00"),
            is_available=True,
        )
        self.tilapia = FoodItem.objects.create(
            category=self.category,
            name="Grilled Tilapia",
            price=Decimal("120.00"),
            is_available=True,
        )

    def test_cart_owner_validation_and_totals(self):
        # Cart without user and without session_key must fail validation
        empty_owner_cart = Cart()
        with self.assertRaises(ValidationError):
            empty_owner_cart.save()

        # Guest session cart works
        guest_cart = Cart.objects.create(session_key="guest-sess-12345")
        self.assertEqual(guest_cart.subtotal, Decimal("0.00"))

        # User cart and CartItems compute line_total, subtotal, and total_items
        user_cart = Cart.objects.create(user=self.customer)
        item1 = CartItem.objects.create(cart=user_cart, fooditem=self.jollof, quantity=2)
        item2 = CartItem.objects.create(cart=user_cart, fooditem=self.tilapia, quantity=1)

        self.assertEqual(item1.unit_price, Decimal("80.00"))
        self.assertEqual(item1.line_total, Decimal("160.00"))
        self.assertEqual(item2.line_total, Decimal("120.00"))
        self.assertEqual(user_cart.total_items, 3)
        self.assertEqual(user_cart.subtotal, Decimal("280.00"))

        # Duplicate fooditem in the same cart violates unique constraint
        with self.assertRaises(IntegrityError):
            CartItem.objects.create(cart=user_cart, fooditem=self.jollof, quantity=1)

    def test_order_reference_and_address_and_item_price_snapshots(self):
        order = Order.objects.create(
            customer=self.customer,
            address=self.address,
            payment_method=PaymentMethod.CARD,
            subtotal=Decimal("160.00"),
            delivery_fee=Decimal("15.00"),
            total=Decimal("175.00"),
        )
        self.assertTrue(order.reference.startswith("ORD-"))
        self.assertLessEqual(len(order.reference), 24)
        self.assertEqual(order.delivery_line1, "15 Cantonments Road")
        self.assertEqual(order.delivery_city, "Accra")
        self.assertEqual(order.delivery_state, "Greater Accra")

        order_item = OrderItem.objects.create(
            order=order,
            fooditem=self.jollof,
            quantity=2,
        )
        self.assertEqual(order_item.name_snapshot, "Special Jollof")
        self.assertEqual(order_item.unit_price, Decimal("80.00"))
        self.assertEqual(order_item.line_total, Decimal("160.00"))

        # Changing the menu FoodItem name/price or editing the customer Address later
        # MUST NOT change historical Order or OrderItem snapshots!
        self.jollof.name = "Renamed Jollof"
        self.jollof.price = Decimal("150.00")
        self.jollof.save()
        self.address.line1 = "99 New Street"
        self.address.save()

        order.refresh_from_db()
        order_item.refresh_from_db()
        self.assertEqual(order.delivery_line1, "15 Cantonments Road")
        self.assertEqual(order_item.name_snapshot, "Special Jollof")
        self.assertEqual(order_item.unit_price, Decimal("80.00"))
        self.assertEqual(order_item.line_total, Decimal("160.00"))

    def test_order_and_status_history_immutability(self):
        order = Order.objects.create(
            customer=self.customer,
            address=self.address,
            subtotal=Decimal("80.00"),
            delivery_fee=Decimal("10.00"),
            total=Decimal("90.00"),
        )
        history = OrderStatusHistory.objects.create(
            order=order,
            status=OrderStatus.PENDING,
            changed_by=self.customer,
            note="Order placed",
        )

        # Updating an existing OrderStatusHistory record must raise ValidationError
        history.note = "Tampered note"
        with self.assertRaises(ValidationError):
            history.save()

        with self.assertRaises(ValidationError):
            OrderStatusHistory.objects.filter(pk=history.pk).update(note="Bulk tamper")

        # Deleting OrderStatusHistory or Order must raise ValidationError
        with self.assertRaises(ValidationError):
            history.delete()

        with self.assertRaises(ValidationError):
            OrderStatusHistory.objects.filter(pk=history.pk).delete()

        with self.assertRaises(ValidationError):
            order.delete()
