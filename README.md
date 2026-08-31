# Restaurant Management System

Django 5.2 LTS system for managing a single restaurant (not SaaS, not
multi-tenant). Built following the project's Master Development Guide.

## Status: backend complete

All planned apps are built out:

- **core** — settings/config package, root URLs, shared `TimeStampedModel`
- **accounts** — custom User model, roles (Administrator/Manager/Cashier/Waiter),
  login/logout/profile/change password/forgot password
- **dashboard** — role-filtered live statistics and Chart.js-ready data
- **menu** — categories and menu items, soft-deletable, searchable/paginated
- **customers** — customer records, searchable/paginated
- **tables** — table status management (Available/Occupied/Reserved/Cleaning/Out of Service)
- **orders** — the core business module: orders, order items with snapshot
  pricing, status/payment workflows, automatic table assignment/release
- **reports** — read-only analytics (revenue, sales, orders, customers,
  table utilization) for Administrators and Managers

Every app follows the same layered structure (`models.py`, `services.py`
for business logic, `selectors.py` for read queries, thin `views.py`),
uses soft deletion instead of hard deletes, and ships with its own
test suite.

Frontend styling is intentionally minimal throughout — templates are
functional placeholders (Tailwind CDN, no custom design system yet).
Payment gateway integration (e.g. Paystack) and PDF/Excel report
exports are deliberately not implemented; the architecture is ready
for both without requiring model changes.

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # then fill in real values

python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

> This code was generated in a sandboxed environment without internet
> access, so it has never actually been run — Django itself isn't
> installed there. `makemigrations` has never been run either, so no
> migration files exist yet; the command above generates them from
> the models before the first `migrate`. Run the full test suite
> locally (`python manage.py test`) before relying on this.

## Project structure

```
restaurant_management/
├── core/           # settings, root urls, wsgi/asgi, shared base model
├── accounts/
├── dashboard/
├── menu/
├── orders/
├── customers/
├── tables/
├── reports/
├── templates/
│   ├── base.html
│   └── includes/   # navbar, sidebar, footer
├── static/
│   ├── css/ js/ images/ icons/ fonts/ vendors/
└── docs/
```
