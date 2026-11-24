"""
Orders domain models (Phase 1 — Developer 3):
  - OrderStatus & PaymentMethod enums
  - Cart (orders_cart)
  - CartItem (orders_cartitem)
  - Order (orders_order)
  - OrderItem (orders_orderitem)
  - OrderStatusHistory (orders_orderstatushistory)
Matches docs/schema.sql and PRD §4.3, §4.4, §4.11, §4.12, §5 (immutability).
Owned by Developer 3.
"""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.core.utils import format_currency, generate_unique_reference, quantize_money


class OrderStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    CONFIRMED = "CONFIRMED", "Confirmed"
    PREPARING = "PREPARING", "Preparing"
    READY_FOR_PICKUP = "READY_FOR_PICKUP", "Ready for Pickup"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Out for Delivery"
    DELIVERED = "DELIVERED", "Delivered"
    CANCELLED = "CANCELLED", "Cancelled"


class PaymentMethod(models.TextChoices):
    CARD = "CARD", "Card / Online (Paystack)"
    CASH = "CASH", "Cash on Delivery"


class Cart(TimeStampedModel):
    """
    Shopping cart model (orders_cart).
    Supports both authenticated customers (user) and guest sessions (session_key).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="carts",
    )
    session_key = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        db_table = "orders_cart"
        verbose_name = "Shopping Cart"
        verbose_name_plural = "Shopping Carts"
        indexes = [
            models.Index(fields=["user"], name="idx_cart_user"),
            models.Index(fields=["session_key"], name="idx_cart_session"),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(user__isnull=False) | (Q(session_key__isnull=False) & ~Q(session_key="")),
                name="chk_cart_owner",
            ),
        ]

    def __str__(self) -> str:
        owner = self.user.username if self.user_id else f"session:{self.session_key}"
        return f"Cart({owner})"

    def clean(self):
        super().clean()
        if not self.user_id and not (self.session_key and self.session_key.strip()):
            raise ValidationError("A cart must belong to either an authenticated user or a session_key.")

    def save(self, *args, **kwargs):
        if self.session_key is not None:
            self.session_key = self.session_key.strip() or None
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def subtotal(self) -> Decimal:
        total = sum((item.line_total for item in self.items.all()), Decimal("0.00"))
        return quantize_money(total)

    @property
    def total_items(self) -> int:
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    """
    Shopping cart line item (orders_cartitem).
    """

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )
    fooditem = models.ForeignKey(
        "menu.FoodItem",
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        db_table = "orders_cartitem"
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "fooditem"],
                name="uq_cartitem_cart_fooditem",
            ),
            models.CheckConstraint(
                check=Q(quantity__gt=0),
                name="chk_cartitem_quantity_positive",
            ),
            models.CheckConstraint(
                check=Q(unit_price__gte=Decimal("0.00")),
                name="chk_cartitem_unit_price_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.quantity} x {self.fooditem.name} in Cart #{self.cart_id}"

    @property
    def line_total(self) -> Decimal:
        return quantize_money(self.unit_price * self.quantity)

    def save(self, *args, **kwargs):
        if self.unit_price is None and self.fooditem_id:
            self.unit_price = self.fooditem.price
        if self.unit_price is not None:
            self.unit_price = quantize_money(self.unit_price)
        super().save(*args, **kwargs)


class ImmutableOrderQuerySet(models.QuerySet):
    def delete(self):
        raise ValidationError("Order records are immutable and cannot be hard-deleted.")


class Order(TimeStampedModel):
    """
    Customer order record (orders_order).
    Preserves delivery address snapshots and computed fee snapshots at checkout time.
    Historical order records cannot be hard-deleted (PRD §5 Data Integrity & schema.sql).
    """

    reference = models.CharField(max_length=24, unique=True, blank=True)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="orders",
    )
    address = models.ForeignKey(
        "accounts.Address",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    status = models.CharField(
        max_length=24,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        db_index=True,
    )
    payment_method = models.CharField(
        max_length=10,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CARD,
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    discount_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    delivery_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    # Delivery address snapshot (preserved even if the saved Address is later edited or deleted)
    delivery_line1 = models.CharField(max_length=255, blank=True, null=True)
    delivery_city = models.CharField(max_length=100, blank=True, null=True)
    delivery_state = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    needs_manual_review = models.BooleanField(
        default=False,
        help_text="Flagged when DISTANCE fee mode falls back to flat fee due to missing GPS coordinates.",
    )
    placed_at = models.DateTimeField(default=timezone.now)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True, null=True)

    objects = ImmutableOrderQuerySet.as_manager()

    class Meta:
        db_table = "orders_order"
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-placed_at"]
        indexes = [
            models.Index(fields=["customer", "-placed_at"], name="idx_order_customer"),
            models.Index(fields=["status"], name="idx_order_status"),
            models.Index(fields=["-placed_at"], name="idx_order_placed"),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(subtotal__gte=Decimal("0.00")),
                name="chk_order_subtotal_non_negative",
            ),
            models.CheckConstraint(
                check=Q(discount_total__gte=Decimal("0.00")),
                name="chk_order_discount_non_negative",
            ),
            models.CheckConstraint(
                check=Q(delivery_fee__gte=Decimal("0.00")),
                name="chk_order_delivery_fee_non_negative",
            ),
            models.CheckConstraint(
                check=Q(total__gte=Decimal("0.00")),
                name="chk_order_total_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.reference} ({self.status} - {self.formatted_total})"

    @property
    def formatted_total(self) -> str:
        return format_currency(self.total)

    def _generate_unique_order_reference(self) -> str:
        ref = generate_unique_reference("ORD")
        while Order.objects.filter(reference=ref).exists():
            ref = generate_unique_reference("ORD")
        return ref

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._generate_unique_order_reference()
        if self.address and not self.delivery_line1:
            self.delivery_line1 = self.address.line1
            self.delivery_city = self.address.city
            self.delivery_state = self.address.state
        self.subtotal = quantize_money(self.subtotal)
        self.discount_total = quantize_money(self.discount_total)
        self.delivery_fee = quantize_money(self.delivery_fee)
        self.total = quantize_money(self.total)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Order records are immutable and cannot be hard-deleted.")


class OrderItem(models.Model):
    """
    Order line item (orders_orderitem).
    Preserves name_snapshot and unit_price at purchase time so later menu edits
    never alter historical order totals.
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    fooditem = models.ForeignKey(
        "menu.FoodItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )
    name_snapshot = models.CharField(max_length=150)
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )
    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        db_table = "orders_orderitem"
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
        indexes = [
            models.Index(fields=["order"], name="idx_orderitem_order"),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(unit_price__gte=Decimal("0.00")),
                name="chk_orderitem_unit_price_non_negative",
            ),
            models.CheckConstraint(
                check=Q(quantity__gt=0),
                name="chk_orderitem_quantity_positive",
            ),
            models.CheckConstraint(
                check=Q(line_total__gte=Decimal("0.00")),
                name="chk_orderitem_line_total_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.quantity} x {self.name_snapshot} ({self.order.reference})"

    def save(self, *args, **kwargs):
        if self.pk is None and self.fooditem_id:
            if not self.name_snapshot:
                self.name_snapshot = self.fooditem.name
            if self.unit_price is None:
                self.unit_price = self.fooditem.price
        self.unit_price = quantize_money(self.unit_price)
        self.line_total = quantize_money(self.unit_price * self.quantity)
        super().save(*args, **kwargs)


class ImmutableStatusHistoryQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("OrderStatusHistory records are immutable and cannot be updated.")

    def delete(self):
        raise ValidationError("OrderStatusHistory records are immutable and cannot be deleted.")


class OrderStatusHistory(models.Model):
    """
    Full immutable audit trail of every order status transition (orders_orderstatushistory).
    PRD §4.4 & §5: Every status transition must be written to an immutable status-history record.
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    status = models.CharField(
        max_length=24,
        choices=OrderStatus.choices,
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_status_changes",
    )
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ImmutableStatusHistoryQuerySet.as_manager()

    class Meta:
        db_table = "orders_orderstatushistory"
        verbose_name = "Order Status History"
        verbose_name_plural = "Order Status Histories"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["order", "created_at"], name="idx_status_history_order"),
        ]

    def __str__(self) -> str:
        actor = self.changed_by.username if self.changed_by_id else "system"
        return f"{self.order.reference} -> {self.status} by {actor}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("OrderStatusHistory records are immutable and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("OrderStatusHistory records are immutable and cannot be deleted.")
