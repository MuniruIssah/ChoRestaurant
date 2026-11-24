# Developer 3 Actionable TODO Checklist — Order Management, Checkout & Payments

**Target Branch:** `feature/dev3-orders-payments` (branched from `develop` / `feature/dev1-infrastructure`)  
**Owned Modules:** `apps/orders/`, `apps/payments/`  
**Shared Update Allowed:** `config/urls.py` (to mount `orders` and `payments` web/API routes)

---

## Phase 0 — Git Branch Setup (When Starting Next Session)
- [x] Switch to or create Developer 3 branch:
  ```powershell
  git checkout -b feature/dev3-orders-payments
  ```

---

## Phase 1 — Cart & Order Domain Models (`apps/orders/models.py`)
Reference: [docs/schema.sql](file:///c:/Users/emman/Desktop/ChoRestaurant/docs/schema.sql#L219-L297)
- [x] **1.1 Define Enums (`models.TextChoices`):**
  - `OrderStatus`: `PENDING`, `CONFIRMED`, `PREPARING`, `READY_FOR_PICKUP`, `OUT_FOR_DELIVERY`, `DELIVERED`, `CANCELLED`
  - `PaymentMethod`: `CARD`, `CASH`
- [x] **1.2 Implement `Cart` (`orders_cart`):**
  - `user` (nullable FK to `settings.AUTH_USER_MODEL`, `on_delete=CASCADE`)
  - `session_key` (`VARCHAR(64)`, nullable for guest carts)
  - Check constraint: `user IS NOT NULL OR session_key IS NOT NULL`
  - `created_at`, `updated_at` (inherit `TimeStampedModel` from `apps.core.models`)
- [x] **1.3 Implement `CartItem` (`orders_cartitem`):**
  - `cart` (FK to `Cart`, `on_delete=CASCADE`, `related_name="items"`)
  - `fooditem` (FK to `apps.menu.models.FoodItem`, `on_delete=CASCADE`)
  - `quantity` (`PositiveIntegerField(default=1)`, check `quantity > 0`)
  - `unit_price` (`DecimalField(max_digits=12, decimal_places=2)`)
  - `unique_together = ("cart", "fooditem")`
- [x] **1.4 Implement `Order` (`orders_order`):**
  - `reference` (`CharField(max_length=24, unique=True)` — generated via `generate_unique_reference("ORD")` from `apps.core.utils`)
  - `customer` (FK to `settings.AUTH_USER_MODEL`, `on_delete=RESTRICT`, `related_name="orders"`)
  - `address` (nullable FK to `apps.accounts.models.Address`, `on_delete=SET_NULL`)
  - `status` (`CharField(choices=OrderStatus.choices, default=OrderStatus.PENDING, db_index=True)`)
  - `payment_method` (`CharField(choices=PaymentMethod.choices, default=PaymentMethod.CARD)`)
  - Money fields (`DecimalField(max_digits=12, decimal_places=2, default=0)`): `subtotal`, `discount_total`, `delivery_fee`, `total`
  - Delivery address snapshot fields: `delivery_line1`, `delivery_city`, `delivery_state`, `notes`
  - Audit flags: `needs_manual_review` (`BooleanField(default=False)` — set if distance mode falls back to flat fee due to missing GPS coordinates)
  - Timestamps: `placed_at`, `confirmed_at`, `delivered_at`, `cancelled_at`, `cancellation_reason`, `created_at`, `updated_at`
- [x] **1.5 Implement `OrderItem` (`orders_orderitem`):**
  - `order` (FK to `Order`, `on_delete=CASCADE`, `related_name="items"`)
  - `fooditem` (nullable FK to `apps.menu.models.FoodItem`, `on_delete=SET_NULL`)
  - `name_snapshot` (`CharField(max_length=150)` — immutable record of item name at purchase time)
  - `unit_price` (`DecimalField(max_digits=12, decimal_places=2)` — immutable price snapshot)
  - `quantity` (`PositiveIntegerField`)
  - `line_total` (`DecimalField(max_digits=12, decimal_places=2)`)
- [x] **1.6 Implement `OrderStatusHistory` (`orders_orderstatushistory`):**
  - `order` (FK to `Order`, `on_delete=CASCADE`, `related_name="status_history"`)
  - `status` (`CharField(choices=OrderStatus.choices)`)
  - `changed_by` (nullable FK to `settings.AUTH_USER_MODEL`, `on_delete=SET_NULL`)
  - `note` (`TextField(blank=True, null=True)`)
  - `created_at` (`DateTimeField(auto_now_add=True)`)
  - **Immutability enforcement:** Disallow updating or deleting existing `OrderStatusHistory` records.

---

## Phase 2 — Delivery Fee Engine & Checkout Calculations (`apps/orders/services.py`)
Reference: [docs/PRD.md §4.12](file:///c:/Users/emman/Desktop/ChoRestaurant/docs/PRD.md#L219-L252) & [docs/ARCHITECTURE.md §4.5](file:///c:/Users/emman/Desktop/ChoRestaurant/docs/ARCHITECTURE.md#L139-L150)
- [ ] **2.1 Delivery Fee Calculator (`calculate_delivery_fee(address, subtotal, promo_free_delivery=False)`):**
  - Read settings from `RestaurantSettings.get_solo()` (`apps.core.models`).
  - Free delivery check: return `Decimal("0.00")` if `free_delivery_threshold` is met (`subtotal >= free_delivery_threshold`) or `promo_free_delivery=True`.
  - `FLAT` mode: return `quantize_money(settings.flat_delivery_fee)`.
  - `DISTANCE` mode:
    - If `address` has GPS coordinates (`address.has_coordinates`), call `MapsFacade.evaluate_destination(address.latitude, address.longitude)`.
    - If `not route.within_delivery_radius` (`distance_km > max_delivery_radius_km`), raise `ValidationError("Delivery address is outside our maximum delivery radius.")`.
    - Compute `base_delivery_fee + max(0, ceil(distance_km - base_distance_km)) * per_km_fee`, rounded to nearest whole currency unit (`GHS`).
    - If coordinates are missing in `DISTANCE` mode, fall back to `flat_delivery_fee` and flag order with `needs_manual_review = True`.
- [ ] **2.2 Server-Side Checkout & Order Creation (`create_order_from_cart(user, address_id, payment_method, notes="")`):**
  - Recompute all item prices from `FoodItem.price` server-side (never trust client-submitted totals).
  - Verify all cart items are `is_orderable` (`is_available` and category `is_active`).
  - Snapshot `name_snapshot`, `unit_price`, and `line_total` onto `OrderItem`.
  - Snapshot `delivery_line1`, `delivery_city`, `delivery_state`, and computed `delivery_fee` onto `Order`.
  - Write initial `OrderStatusHistory(status=PENDING)` (or `CONFIRMED` for `CASH` on delivery per PRD §4.13).

---

## Phase 3 — Order Status Lifecycle & Cancellation Rules (`apps/orders/services.py`)
Reference: [docs/PRD.md §4.4 & §4.11](file:///c:/Users/emman/Desktop/ChoRestaurant/docs/PRD.md#L68-L87)
- [ ] **3.1 Valid Status Transition Matrix (`transition_order_status(order, new_status, actor, note="")`):**
  - Enforce valid state machine transitions:
    - `PENDING` $\rightarrow$ `CONFIRMED` | `CANCELLED`
    - `CONFIRMED` $\rightarrow$ `PREPARING` | `CANCELLED`
    - `PREPARING` $\rightarrow$ `READY_FOR_PICKUP` | `CANCELLED` (Staff/Admin only)
    - `READY_FOR_PICKUP` $\rightarrow$ `OUT_FOR_DELIVERY` | `CANCELLED` (Staff/Admin only)
    - `OUT_FOR_DELIVERY` $\rightarrow$ `DELIVERED` | `CANCELLED` (Admin only for cancel)
    - `DELIVERED` and `CANCELLED` are terminal states.
  - Record every transition in `OrderStatusHistory` with `changed_by=actor` and `note`.
- [ ] **3.2 Cancellation & Refund Triggers (`cancel_order(order, actor, reason)`):**
  - Customers can cancel only while `status in (PENDING, CONFIRMED)`.
  - Once `PREPARING` or later, only `STAFF` or `ADMIN` can cancel (with mandatory `reason`).
  - `DELIVERED` orders can never be cancelled.
  - If a `CARD` order with a `SUCCESS` payment is cancelled while `PENDING`/`CONFIRMED`, automatically initiate/mark refund on the payment record.
- [ ] **3.3 Unpaid Order Timeout Task (`apps/orders/tasks.py`):**
  - Celery task `cancel_expired_unpaid_orders`: automatically cancels `PENDING` card orders unpaid after **15 minutes** (PRD §4.13).

---

## Phase 4 — Payment Model, Paystack & Cash-on-Delivery (`apps/payments/`)
Reference: [docs/PRD.md §4.13](file:///c:/Users/emman/Desktop/ChoRestaurant/docs/PRD.md#L253-L275) & [docs/ARCHITECTURE.md §6](file:///c:/Users/emman/Desktop/ChoRestaurant/docs/ARCHITECTURE.md#L166-L175)
- [ ] **4.1 Implement `Payment` (`payments_payment`) in `apps/payments/models.py`:**
  - `PaymentStatus`: `PENDING`, `SUCCESS`, `FAILED`, `REFUNDED`
  - `order` (FK to `orders.Order`, `on_delete=RESTRICT`, `related_name="payments"`)
  - `reference` (`CharField(max_length=64, unique=True)`)
  - `provider` (`CharField(max_length=30, default="PAYSTACK")`) — `"PAYSTACK"` or `"CASH"`
  - `amount` (`DecimalField(max_digits=12, decimal_places=2)`)
  - `currency` (`CharField(max_length=3, default="GHS")`)
  - `status` (`CharField(choices=PaymentStatus.choices, default=PaymentStatus.PENDING)`)
  - `authorization_url`, `provider_reference`, `paid_at`, `raw_response` (`JSONField(null=True, blank=True)`)
  - `created_at`, `updated_at`
- [ ] **4.2 Paystack Initialization & Server-Side Verification (`apps/payments/services.py`):**
  - `initialize_paystack_payment(order)`: Creates `Payment(status=PENDING)`, calls Paystack `/transaction/initialize` (or clean mock/adapter when `PAYSTACK_SECRET_KEY` is in test mode), returns `authorization_url` and `reference`.
  - `verify_paystack_payment(reference)`: Calls Paystack `/transaction/verify/<reference>`, checks `status == "success"`, verifies `amount == order.total` and `currency == "GHS"`.
  - On amount/currency mismatch or failure: mark `Payment.status = FAILED`, keep `Order.status = PENDING`, store `raw_response`.
  - On valid success: mark `Payment.status = SUCCESS`, set `paid_at`, transition `Order` to `CONFIRMED`.
- [ ] **4.3 Idempotent HMAC-Verified Paystack Webhook (`POST /api/payments/webhook/`):**
  - Validate `x-paystack-signature` header using HMAC SHA-512 with `settings.PAYSTACK_SECRET_KEY`.
  - Ignore duplicate webhook replays if `Payment.status == SUCCESS` (idempotent).
- [ ] **4.4 Payment Retries & Cash-on-Delivery:**
  - Failed online payments allow retry by creating a new `Payment` reference tied to the `Order`.
  - Cash-on-delivery (`CASH`): confirms `Order` immediately while `Payment` stays `PENDING` (`provider="CASH"`) until marked `SUCCESS` upon delivery (or `FAILED` if delivery fails).

---

## Phase 5 — APIs, Admin, Wiring & Unit Tests
- [ ] **5.1 REST API & Web Views (`apps/orders/` & `apps/payments/`):**
  - Cart endpoints: `GET/POST /api/orders/cart/`, `PATCH/DELETE /api/orders/cart/items/<id>/`
  - Checkout & Fee Preview: `POST /api/orders/delivery-fee-preview/`, `POST /api/orders/checkout/`
  - Order list/detail/cancel/status: `GET /api/orders/`, `GET /api/orders/<reference>/`, `POST /api/orders/<reference>/cancel/`, `POST /api/orders/<reference>/status/`
  - Payment endpoints: `POST /api/payments/initialize/`, `GET /api/payments/verify/<reference>/`, `POST /api/payments/webhook/`, `POST /api/payments/<reference>/retry/`
- [ ] **5.2 Mount URLs in `config/urls.py` & Register Models in Django Admin (`admin.py`).**
- [ ] **5.3 Write Comprehensive Unit Tests (`apps/orders/tests.py` & `apps/payments/tests.py`):**
  - Cart operations & price snapshot preservation when `FoodItem.price` changes later
  - Flat vs. distance delivery fee calculation, free-delivery threshold, out-of-radius rejection, and missing-GPS fallback
  - Order status transition matrix, immutable `OrderStatusHistory`, and customer vs. staff cancellation rules
  - Paystack verification, HMAC webhook signature validation, replay idempotency, amount mismatch failure, payment retries, and cash-on-delivery lifecycle.
