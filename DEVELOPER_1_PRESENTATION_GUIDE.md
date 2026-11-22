# Developer 1 Master Presentation & Defense Guide
## Restaurant Ordering & Delivery Management System (Cho Restaurant)

**Your Role:** Developer 1 — Backend Infrastructure, Authentication, Database & Menu Foundation  
**Your Git Branch:** `feature/dev1-infrastructure`  
**Your Owned Modules:** `config/`, `apps/core/`, `apps/accounts/`, `apps/menu/`

---

## 1. Your 60-Second Opening Pitch (Memorize This)

> *"Good day everyone. In our five-developer team for the **Cho Restaurant Ordering & Delivery Management System**, I am **Developer 1**, responsible for the **Backend Infrastructure, Authentication, Role-Based Access Control, Database Foundation, and Menu Management**.*
>
> *My work forms the architectural backbone that Developers 2 through 5 depend on. Specifically, I initialized the Django 5 project with a modular three-environment settings split, resolved the project's localization requirement for **Ghana (`GHS` / `GH₵`)**, engineered the custom `User` model and role-permission framework **before** the initial database migration, built automatic customer and dispatch-rider profile provisioning with saved GPS delivery addresses, and implemented the food category and menu administration backend with full REST APIs, Django Admin dashboards, and 19 automated unit tests."*

---

## 2. How Your Work Powers the Other Four Developers

Use this table if asked how your code integrates with the rest of the team:

| Teammate | Their Module | What They Import / Consume From Your Code |
|---|---|---|
| **Developer 2** (Customer Website) | `templates/customer/`, `static/` | Uses your `/accounts/` and `/menu/` views & forms, `/api/accounts/` and `/api/menu/` JSON endpoints, and global template context variables (`CURRENCY_SYMBOL`, `CURRENT_USER_ROLE`, `IS_CUSTOMER`). |
| **Developer 3** (Orders & Payments) | `apps/orders/`, `apps/payments/` | Links orders to your `accounts.User`, `accounts.Address`, and `menu.FoodItem` models; reads delivery-fee rules from your `RestaurantSettings.get_solo()`; calculates distances with your `MapsFacade`; uses `quantize_money()` and `generate_unique_reference()`. |
| **Developer 4** (Delivery & Live GPS) | `apps/delivery/`, `apps/notifications/` | Uses your `accounts.RiderProfile` model, `get_available_riders()` service, consent-gated `update_location()` method, and your baseline `config/asgi.py` & `config/celery.py`. |
| **Developer 5** (Admin, Promos, Reviews & QA) | `apps/dashboard/`, `apps/promotions/`, `apps/reviews/` | Uses your `StaffOrAdminRequiredMixin`, `AdminRequiredMixin`, `RestaurantSettings` for delivery-fee configuration, and `FoodItem` for review averages and promotional campaigns. |

---

## 3. Deep-Dive Breakdown of Your 9 Core Tasks (Know the "What" and "Why")

### Task 1 & 2: Project Initialization, PostgreSQL Configuration & Settings Split (`config/settings/`)
- **Files:** [config/settings/base.py](file:///c:/Users/emman/Desktop/ChoRestaurant/config/settings/base.py), [config/settings/dev.py](file:///c:/Users/emman/Desktop/ChoRestaurant/config/settings/dev.py), [config/settings/prod.py](file:///c:/Users/emman/Desktop/ChoRestaurant/config/settings/prod.py)
- **What you built:**
  - `base.py`: Central configuration shared across all environments—registers all 10 project apps, sets `AUTH_USER_MODEL = "accounts.User"`, configures Django REST Framework, Redis/Celery broker settings, and defines localization defaults (`DEFAULT_COUNTRY = "Ghana"`, `DEFAULT_CURRENCY = "GHS"`, `CURRENCY_SYMBOL = "GH₵"`, `TIME_ZONE = "Africa/Accra"`).
  - `dev.py`: Reads `DATABASE_URL` to connect to PostgreSQL 16 when provided, and automatically falls back to local SQLite (`db.sqlite3`) and in-memory Channels so any developer on the team can clone the repo and run tests immediately without environment blockers.
  - `prod.py`: Enforces strict security (`DEBUG = False`, requires `DJANGO_SECRET_KEY` and PostgreSQL `DATABASE_URL` with connection pooling `CONN_MAX_AGE = 600`), enables HTTPS/HSTS/secure cookies, Redis cache/channel layers, and Cloudinary media storage.

### Task 3: Custom User Model Before the First Migration (`apps/accounts/models.py`)
- **Files:** [apps/accounts/models.py](file:///c:/Users/emman/Desktop/ChoRestaurant/apps/accounts/models.py), [apps/accounts/managers.py](file:///c:/Users/emman/Desktop/ChoRestaurant/apps/accounts/managers.py)
- **What you built:**
  - `User(AbstractUser)` mapped to table `accounts_user` (matching [docs/schema.sql](file:///c:/Users/emman/Desktop/ChoRestaurant/docs/schema.sql)).
  - Added `email` (unique, indexed, auto-normalized to lowercase), `phone`, `role` (`CUSTOMER`, `STAFF`, `RIDER`, `ADMIN`), `is_email_verified`, `created_at`, and `updated_at`.
  - Custom `UserManager` where `create_superuser()` automatically assigns `role = "ADMIN"`, `is_staff = True`, and `is_superuser = True`.
- **Why before the first migration?**
  - Django's `auth`, `admin`, and `contenttypes` migrations build foreign keys pointing to `AUTH_USER_MODEL`. Switching to a custom user model *after* running the first migration corrupts the migration dependency graph. Defining it first guarantees a clean database schema from `0001_initial`.

### Task 4: Role-Based Access Control (RBAC) (`apps/core/permissions.py`)
- **File:** [apps/core/permissions.py](file:///c:/Users/emman/Desktop/ChoRestaurant/apps/core/permissions.py)
- **What you built:** Three complete enforcement layers so every developer can protect their endpoints server-side:
  1. **Class-Based View Mixins:** `RoleRequiredMixin`, `CustomerRequiredMixin`, `StaffRequiredMixin`, `RiderRequiredMixin`, `AdminRequiredMixin`, `StaffOrAdminRequiredMixin`.
  2. **Function-Based View Decorators:** `@role_required(*roles)`, `@customer_required`, `@staff_required`, `@rider_required`, `@admin_required`, `@staff_or_admin_required`.
  3. **DRF API Permission Classes:** `IsCustomer`, `IsStaff`, `IsRider`, `IsAdminRole`, `IsStaffOrAdmin`, `IsOwnerOrAdmin`, `ReadOnlyOrStaffAdmin`.

### Task 5: Authentication, Customer Profiles & Saved Delivery Addresses (`apps/accounts/`)
- **Files:** [apps/accounts/models.py](file:///c:/Users/emman/Desktop/ChoRestaurant/apps/accounts/models.py), [apps/accounts/signals.py](file:///c:/Users/emman/Desktop/ChoRestaurant/apps/accounts/signals.py), [apps/accounts/services.py](file:///c:/Users/emman/Desktop/ChoRestaurant/apps/accounts/services.py), [apps/accounts/views.py](file:///c:/Users/emman/Desktop/ChoRestaurant/apps/accounts/views.py), [apps/accounts/api_views.py](file:///c:/Users/emman/Desktop/ChoRestaurant/apps/accounts/api_views.py)
- **What you built:**
  - **Dual-Identifier Login:** `authenticate_user()` allows users to log in with **either their username or email address**.
  - **Automatic Profile Provisioning (`signals.py`):** A `post_save` signal on `User` automatically creates a `CustomerProfile` when a `CUSTOMER` registers, or a `RiderProfile` when a `RIDER` is created.
  - **Notification Preferences (`CustomerProfile`):** Implements PRD §4.9—customers can toggle `notify_email` and `notify_sms`, while `notify_in_app` is enforced as always `True` so critical order status updates are never missed.
  - **Saved Delivery Addresses (`Address`):** Supports multiple addresses per user (`Home`, `Office`, etc.) with GPS coordinates (`latitude`, `longitude`) and default country `'Ghana'`. Saving a first address or marking an address `is_default=True` automatically unsets previous defaults inside an atomic database transaction and updates `CustomerProfile.default_address`.

### Task 6: Rider Profile Models & Shared Backend Utilities (`apps/accounts/` & `apps/core/`)
- **Files:** [apps/accounts/models.py](file:///c:/Users/emman/Desktop/ChoRestaurant/apps/accounts/models.py), [apps/core/models.py](file:///c:/Users/emman/Desktop/ChoRestaurant/apps/core/models.py), [apps/core/maps.py](file:///c:/Users/emman/Desktop/ChoRestaurant/apps/core/maps.py), [apps/core/utils.py](file:///c:/Users/emman/Desktop/ChoRestaurant/apps/core/utils.py)
- **What you built:**
  - **`RiderProfile` (`accounts_riderprofile`):** Stores `vehicle_type` (`MOTORCYCLE`, `BICYCLE`, `CAR`, `VAN`), `plate_number`, `is_available`, `is_verified`, `location_consent`, `current_lat`, `current_lng`, and `last_seen`.
  - **Privacy & Consent Enforcement:** `rider_profile.update_location(lat, lng)` raises a `ValidationError` unless `location_consent=True` (enforcing PRD §4.6), and `clear_location()` wipes coordinates when a delivery finishes.
  - **Shared Base Models:** `TimeStampedModel` and `SoftDeleteModel` (so orders, reviews, and audit records are soft-deleted rather than hard-deleted).
  - **Cached Singleton `RestaurantSettings`:** Stores the restaurant's GPS origin in Accra (`5.603717, -0.186964`) and delivery-fee thresholds (`FLAT` vs `DISTANCE`, base fee, per-km fee, max delivery radius, free delivery threshold) in cache (`RestaurantSettings.get_solo()`).
  - **`MapsFacade`:** Calculates great-circle distance in kilometers using the **Haversine formula**, verifies if an address is within `max_delivery_radius_km`, and estimates travel time in minutes.
  - **Financial Precision:** `quantize_money()` forces `Decimal("0.01")` (`ROUND_HALF_UP`) so money is never processed as floating-point numbers.

### Task 7: Food Categories, Food Items & Menu Administration Backend (`apps/menu/`)
- **Files:** [apps/menu/models.py](file:///c:/Users/emman/Desktop/ChoRestaurant/apps/menu/models.py), [apps/menu/services.py](file:///c:/Users/emman/Desktop/ChoRestaurant/apps/menu/services.py), [apps/menu/admin.py](file:///c:/Users/emman/Desktop/ChoRestaurant/apps/menu/admin.py), [apps/menu/api_views.py](file:///c:/Users/emman/Desktop/ChoRestaurant/apps/menu/api_views.py)
- **What you built:**
  - **`Category` (`menu_category`):** `name`, auto-generated unique `slug`, `description`, `image`, `sort_order`, `is_active`.
  - **`FoodItem` (`menu_fooditem`):** `category` (`on_delete=models.RESTRICT` so categories with food items cannot be accidentally deleted), `name`, unique `slug`, `description`, `price` (`NUMERIC(12,2)` with DB check constraint `price >= 0`), `image`, `is_available`, `is_featured` (special meals / daily offers), and `prep_time_minutes`.
  - **Menu Administration & APIs:**
    - Public browsing endpoints (`/api/menu/categories/`, `/api/menu/items/`, `/api/menu/featured/`) with filtering by category, featured flag, and keyword search (`?search=jollof`).
    - Protected Staff/Admin write endpoints (`ReadOnlyOrStaffAdmin`) and one-click availability toggle (`POST /api/menu/items/<slug>/toggle-availability/`).
    - Full Django Admin interface with inline items, bulk availability/featured actions, and inline editing.

---

## 4. Step-by-Step Live Demo Script (5 Minutes)

Follow these exact steps when you present your screen:

### Step 1: Start the Project with `start.bat` (30 sec)
1. Double-click [start.bat](file:///c:/Users/emman/Desktop/ChoRestaurant/start.bat) (or run `.\start.bat` in terminal).
2. Point out to the audience what the script does automatically:
   - Activates `.venv`
   - Runs `python manage.py migrate`
   - Runs `python manage.py seed_dev1_data` (seeding Ghanaian dishes and 4 role accounts)
   - Opens `http://127.0.0.1:8000/`

### Step 2: Walk Through the Developer 1 Foundation Portal (`http://127.0.0.1:8000/`) (1 min)
1. Highlight the **top summary cards**:
   - 4 seeded role accounts (`CUSTOMER`, `STAFF`, `RIDER`, `ADMIN`)
   - 3 Ghanaian food categories & 7 food items priced in **Ghana Cedis (`GH₵`)**
   - Saved Accra delivery address & verified dispatch rider
2. Scroll down to **Live Menu Data (`apps.menu`)** and show how categories (`Local Dishes`, `Grills & Starters`, `Drinks & Refreshments`), prices (`GH₵85.00`), preparation times, and `Available` / `Featured` tags are rendered directly from the database.

### Step 3: Demonstrate Authentication, Profile & Delivery Addresses (1.5 min)
1. Click **Login** (`/accounts/login/`).
2. Log in as the customer using email or username:
   - Username/Email: `customer_akua` (or `customer@chorestaurant.com`)
   - Password: `CustomerPass123!`
3. Show **My Profile** (`/accounts/profile/`):
   - Point out the role badge (`CUSTOMER`), contact details, and notification preferences (`notify_email`, `notify_sms`).
4. Click **Manage Delivery Addresses** (`/accounts/addresses/`):
   - Show the default address (`14 Independence Avenue, Accra, Greater Accra (Ghana)`) with GPS coordinates (`5.573100, -0.196900`).
   - Add a second address (e.g., Label: `Office`, Line 1: `Osu Oxford Street`, City: `Accra`, State: `Greater Accra`, Country: `Ghana`, check `Is default`). Show how it automatically becomes `[Default]`.

### Step 4: Demonstrate REST APIs & Role Permissions (1 min)
1. Open `/api/health/` to show the live database health check and localization response (`"country": "Ghana", "currency": "GHS"`).
2. Open `/api/menu/items/` and `/api/menu/featured/` to show the structured JSON contracts that Developer 2 (Frontend) and Developer 3 (Orders) consume.
3. Show that because you are logged in as a `CUSTOMER`, trying to `POST` a new menu item is blocked by `ReadOnlyOrStaffAdmin` (`403 Forbidden`).

### Step 5: Demonstrate Django Admin as Administrator (1 min)
1. Log out (`/accounts/logout/`), then open `/admin/` and log in as:
   - Username: `admin_cho`
   - Password: `AdminPass123!`
2. Show **Users**, **Customer Profiles**, **Delivery Addresses**, and **Rider Profiles** (show `location_consent`, `is_verified`, `vehicle_type`).
3. Open **Food Categories** and **Food Items** — demonstrate editing prices, `is_available`, and `is_featured` inline.
4. Open **Restaurant Settings** — show the singleton settings for restaurant GPS coordinates and delivery fee rules (`DISTANCE` mode, base fee, per-km fee, max radius).

---

## 5. Top Questions Examiners May Ask You (With Winning Answers)

### Q1: *"Why did you change the default country and currency from Nigeria/NGN to Ghana/GHS?"*
**Answer:**  
*"Page 9 of our team collaboration document explicitly highlighted an **Important Localization Decision**: the reference SQL schema had `'Nigeria'` and `'NGN'` defaults, whereas our project is developed in Ghana. We confirmed Ghana and `GHS` (`GH₵`) before generating our initial migrations so all database defaults, `RestaurantSettings`, and formatted prices are consistent across all five developers."*

### Q2: *"How do you prevent floating-point rounding errors in food prices and delivery fees?"*
**Answer:**  
*"Following the technical architecture and `schema.sql`, all monetary fields use `DecimalField(max_digits=12, decimal_places=2)` (`NUMERIC(12,2)` in PostgreSQL), never `FloatField`. In `apps/core/utils.py`, I also provided `quantize_money()` using `ROUND_HALF_UP` to two decimal places, and `FoodItem.save()` automatically quantizes prices before saving."*

### Q3: *"How does your system protect rider privacy for live GPS tracking?"*
**Answer:**  
*"Per PRD Section 4.6, GPS location sharing must be consent-gated. In `RiderProfile`, I added a `location_consent` boolean field. The `update_location(lat, lng)` method checks `if not self.location_consent` and raises a `ValidationError` if a location update is attempted without consent. I also included a `clear_location()` method to wipe `current_lat` and `current_lng` once a delivery completes."*

### Q4: *"What happens if Developer 2 hasn't finished the HTML templates yet, or wants to use `fetch()` via JavaScript?"*
**Answer:**  
*"I designed both clean REST API endpoints under `/api/accounts/` and `/api/menu/` AND hybrid web views under `/accounts/` and `/menu/`. The web views automatically look for Developer 2's templates in `templates/customer/` first; if `Accept: application/json` is requested they return JSON, and if the customer templates aren't created yet they render a clean built-in fallback page so backend testing is never blocked."*

### Q5: *"How did you verify that all your models, permissions, and endpoints work?"*
**Answer:**  
*"I wrote 19 automated unit and API integration tests across `apps/core/tests.py`, `apps/accounts/tests.py`, and `apps/menu/tests.py`. They test money quantization, Haversine distance calculation, RBAC mixins/decorators/DRF permissions for all four roles, automatic profile creation via signals, rider GPS consent enforcement, default address synchronization, slug generation, and staff-only menu administration."*
