# Git Workflow & Five-Developer Collaboration Guide

## Branch Architecture

```text
main
└── develop
    ├── feature/dev1-infrastructure
    ├── feature/dev2-customer-website
    ├── feature/dev3-orders-payments
    ├── feature/dev4-delivery-tracking
    └── feature/dev5-admin-reviews
```

| Branch | Owner | Purpose |
|---|---|---|
| `main` | Protected | Stable, tested production code. |
| `develop` | Integration | Combined development and integration code. |
| `feature/dev1-infrastructure` | Developer 1 | Backend foundation, settings, custom `User`, RBAC, `core`, `accounts`, `menu`. |
| `feature/dev2-customer-website` | Developer 2 | Customer templates, CSS/JS, menu UI, cart UI, checkout UI, customer dashboard. |
| `feature/dev3-orders-payments` | Developer 3 | `apps/orders/`, `apps/payments/`, checkout calculations, delivery fees, Paystack. |
| `feature/dev4-delivery-tracking` | Developer 4 | `apps/delivery/`, `apps/notifications/`, `config/asgi.py`, Channels, Celery, GPS. |
| `feature/dev5-admin-reviews` | Developer 5 | `apps/dashboard/`, `apps/promotions/`, `apps/reviews/`, admin/staff UI, tests. |

## Daily Workflow

```bash
# 1. Start from the latest integration branch
git checkout develop
git pull origin develop

# 2. Switch to your developer branch (or create a task branch)
git checkout feature/dev1-infrastructure

# 3. Run checks and unit tests before committing
.venv/Scripts/python manage.py check
.venv/Scripts/python manage.py test

# 4. Stage and commit using Conventional Commits
git add .
git commit -m "feat(accounts): implement custom user model, roles and delivery addresses"
```

## Rules to Prevent Conflicts

1. **Never push directly to `main`.**
2. **Never commit `.env` files, secrets, or local `db.sqlite3`.**
3. **Custom User model (`apps/accounts/models.py`) and `config/settings/` are coordinated by Developer 1.** Request changes via PR review.
4. **Coordinate database migrations** before merging into `develop`.
