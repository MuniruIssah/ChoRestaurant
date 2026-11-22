# Developer Guide — Restaurant Ordering & Delivery Management System

## 1. Local Environment Setup

### Prerequisites
- Python 3.11+ (3.12 tested)
- PostgreSQL 16 (recommended for production/staging; local dev automatically falls back to SQLite if `DATABASE_URL` is blank)
- Redis (required for Channels WebSockets & Celery workers)

### Step-by-Step Setup (Windows PowerShell)

```powershell
# 1. Create and use the project virtual environment
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# 2. Copy environment configuration
Copy-Item .env.example .env

# 3. Apply database migrations (Custom User model is already configured in apps.accounts)
.\.venv\Scripts\python manage.py migrate

# 4. (Optional) Seed Developer 1 foundation data (demo users for all 4 roles + Ghanaian menu items)
.\.venv\Scripts\python manage.py seed_dev1_data

# 5. Run the test suite
.\.venv\Scripts\python manage.py test

# 6. Start the development server
.\.venv\Scripts\python manage.py runserver
```

## 2. Seeded Demo Accounts (`python manage.py seed_dev1_data`)

| Role | Username | Email | Password |
|---|---|---|---|
| `ADMIN` | `admin_cho` | `admin@chorestaurant.com` | `AdminPass123!` |
| `STAFF` | `staff_ama` | `staff@chorestaurant.com` | `StaffPass123!` |
| `RIDER` | `rider_kofi` | `rider@chorestaurant.com` | `RiderPass123!` |
| `CUSTOMER` | `customer_akua` | `customer@chorestaurant.com` | `CustomerPass123!` |

## 3. Module Ownership & Integration Boundaries

- **Developer 1 (`config/`, `apps/core/`, `apps/accounts/`, `apps/menu/`):**
  - Owns `AUTH_USER_MODEL = "accounts.User"`, role permissions (`apps.core.permissions`), `RestaurantSettings.get_solo()`, `MapsFacade`, `CustomerProfile`, `Address`, `RiderProfile`, `Category`, and `FoodItem`.
- **Developer 2 (`templates/customer/`, `static/css/customer/`, `static/js/customer/`):**
  - Can render templates matched by `apps/accounts/views.py` and `apps/menu/views.py` (`customer/login.html`, `customer/register.html`, `customer/profile.html`, `customer/addresses.html`, `customer/menu_list.html`, `customer/category_detail.html`, `customer/food_detail.html`) or call the JSON APIs under `/api/accounts/` and `/api/menu/`.
- **Developer 3 (`apps/orders/`, `apps/payments/`):**
  - Imports `FoodItem` from `apps.menu.models`, `Address` and `User` from `apps.accounts.models`, `RestaurantSettings` from `apps.core.models`, `MapsFacade` from `apps.core.maps`, and `generate_unique_reference` / `quantize_money` from `apps.core.utils`.
- **Developer 4 (`apps/delivery/`, `apps/notifications/`, `config/asgi.py`):**
  - Imports `RiderProfile` from `apps.accounts.models` and `get_available_riders` / `update_rider_gps` from `apps.accounts.services`.
- **Developer 5 (`apps/dashboard/`, `apps/promotions/`, `apps/reviews/`, `tests/`):**
  - Uses `StaffOrAdminRequiredMixin` / `AdminRequiredMixin` from `apps.core.permissions` and edits `RestaurantSettings` for delivery-fee configuration.
