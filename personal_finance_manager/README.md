# Personal Finance Manager

A Flask web app for tracking personal income, expenses, budgets, and spending
reports — built to match the SIWES logbook progression (Weeks 1–12).

## Features

- **Authentication** — register/login with hashed passwords, session-based login.
- **Transactions (CRUD)** — add, edit, delete, and filter income/expense records.
- **Categories** — transactions organized into Food, Transport, Utilities, Savings, Other.
- **Budgeting** — set a monthly budget per category, track spend vs. budget.
- **Dashboard** — income/expense/balance summary, category breakdown, recent activity.
- **Reports** — month-by-month income, expenses, net, and category breakdown.

## Setup

```bash
cd personal_finance_manager
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The app creates `finance.db` (SQLite) and seeds default categories automatically
on first run. Visit **http://127.0.0.1:5000** in your browser.

Alternatively, using the Flask CLI:

```bash
export FLASK_APP=app.py     # Windows: set FLASK_APP=app.py
flask init-db               # creates tables + seeds categories
flask run
```

## Project Structure

```
personal_finance_manager/
├── app.py                  # Routes: auth, dashboard, transactions, budget, reports
├── models.py                # SQLAlchemy models: User, Category, Transaction, Budget
├── requirements.txt
├── templates/                # Jinja2 templates
│   ├── base.html
│   ├── login.html / register.html
│   ├── dashboard.html
│   ├── transactions.html / add_transaction.html / edit_transaction.html
│   ├── budget.html
│   └── reports.html
└── static/
    └── style.css
```

## Notes

- Default SECRET_KEY is for development only — set the `SECRET_KEY` environment
  variable before deploying anywhere real.
- Database is SQLite for simplicity; swap `SQLALCHEMY_DATABASE_URI` for
  Postgres/MySQL in production.
