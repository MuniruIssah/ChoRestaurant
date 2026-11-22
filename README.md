# Cho Restaurant — Ordering & Delivery Management System

A full-stack Restaurant Ordering & Delivery Management System built with **Django 5**, **PostgreSQL 16**, **Django REST Framework**, **Django Channels**, **Redis + Celery**, **Leaflet/OpenStreetMap**, **Paystack**, and **Cloudinary**.

---

## Developer 1 Foundation Status (Completed)

This repository is initialized with the five-developer structure and complete **Developer 1** deliverables:

- **Settings Split (`config/settings/`):** `base.py`, `dev.py` (PostgreSQL via `DATABASE_URL` with automatic SQLite fallback for local development), and `prod.py` (PostgreSQL 16, Cloudinary media storage, Redis cache/Channels, and HSTS/SSL security headers).
- **Custom User & Role-Based Access Control (`apps/accounts/` & `apps/core/permissions.py`):**
  - Custom `accounts.User` (`AUTH_USER_MODEL`) with `CUSTOMER`, `STAFF`, `RIDER`, and `ADMIN` roles created prior to initial database migration.
  - Reusable CBV mixins (`RoleRequiredMixin`, `CustomerRequiredMixin`, `StaffRequiredMixin`, `RiderRequiredMixin`, `AdminRequiredMixin`), FBV decorators (`@role_required`, etc.), and DRF permission classes (`IsCustomer`, `IsStaff`, `IsRider`, `IsAdminRole`, `ReadOnlyOrStaffAdmin`).
- **Profiles & Saved Delivery Addresses (`apps/accounts/`):**
  - Automatic `CustomerProfile` and `RiderProfile` provisioning via signals and services.
  - Saved `Address` management with default address synchronization, GPS coordinates (`latitude`/`longitude`), and **Ghana (`GHS` / `GH₵`)** localization defaults.
  - `RiderProfile` with vehicle details, availability, verification, and consent-gated GPS coordinate updates.
- **Food Categories & Menu Administration Backend (`apps/menu/`):**
  - `Category` and `FoodItem` models matching `docs/schema.sql` with automatic unique slug generation, `NUMERIC(12,2)` price quantization, availability toggles, featured daily offers, Django Admin customization, web views, and REST API endpoints.
- **Shared Core Utilities (`apps/core/`):**
  - `TimeStampedModel`, `SoftDeleteModel`, singleton `RestaurantSettings` (delivery fee thresholds & restaurant GPS origin), `MapsFacade` (Haversine distance, radius verification, ETA estimation), unique reference generator, and template context processors.

---

## Quick Start

```powershell
# 1. Create virtual environment and install dependencies
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# 2. Apply migrations
.\.venv\Scripts\python manage.py migrate

# 3. Seed sample Ghanaian menu items and role accounts
.\.venv\Scripts\python manage.py seed_dev1_data

# 4. Run automated unit tests
.\.venv\Scripts\python manage.py test

# 5. Start the development server
.\.venv\Scripts\python manage.py runserver
```

## Documentation

- [**Developer 1 Master Presentation & Defense Guide**](DEVELOPER_1_PRESENTATION_GUIDE.md)
- [Technical Architecture](docs/ARCHITECTURE.md)
- [Product Requirements Document (PRD)](docs/PRD.md)
- [PostgreSQL 16 Schema](docs/schema.sql)
- [API Contracts & Interface Documentation](docs/API_DOCUMENTATION.md)
- [Git Collaboration Workflow](docs/GIT_WORKFLOW.md)
- [Developer Setup & Integration Guide](docs/DEVELOPER_GUIDE.md)
- [Five-Developer Team Structure](Restaurant_Project_README.md)
