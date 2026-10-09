import os
from datetime import datetime, date
from functools import wraps
from collections import defaultdict

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)

from models import db, User, Category, Transaction, Budget, seed_categories

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + os.path.join(BASE_DIR, "finance.db")
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped_view


def current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return User.query.get(user_id)


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        error = None
        if not username or not email or not password:
            error = "All fields are required."
        elif password != confirm:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif User.query.filter_by(username=username).first():
            error = "That username is already taken."
        elif User.query.filter_by(email=email).first():
            error = "An account with that email already exists."

        if error:
            flash(error, "danger")
            return render_template("register.html", username=username, email=email)

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier.lower())
        ).first()

        if user and user.check_password(password):
            session.clear()
            session["user_id"] = user.id
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username/email or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    if current_user():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    transactions = (
        Transaction.query.filter_by(user_id=user.id)
        .order_by(Transaction.date.desc())
        .all()
    )

    total_income = sum(t.amount for t in transactions if t.type == "income")
    total_expense = sum(t.amount for t in transactions if t.type == "expense")
    balance = total_income - total_expense

    # Breakdown of expenses by category (for the analytics view)
    category_totals = defaultdict(float)
    for t in transactions:
        if t.type == "expense":
            cat_name = t.category.name if t.category else "Uncategorized"
            category_totals[cat_name] += t.amount

    recent_transactions = transactions[:5]

    return render_template(
        "dashboard.html",
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        category_totals=dict(category_totals),
        recent_transactions=recent_transactions,
    )


# ---------------------------------------------------------------------------
# Transactions (CRUD)
# ---------------------------------------------------------------------------

@app.route("/transactions")
@login_required
def transactions_list():
    user = current_user()
    category_id = request.args.get("category_id", type=int)
    type_filter = request.args.get("type")

    query = Transaction.query.filter_by(user_id=user.id)
    if category_id:
        query = query.filter_by(category_id=category_id)
    if type_filter in ("income", "expense"):
        query = query.filter_by(type=type_filter)

    transactions = query.order_by(Transaction.date.desc()).all()
    categories = Category.query.order_by(Category.name).all()

    return render_template(
        "transactions.html",
        transactions=transactions,
        categories=categories,
        selected_category=category_id,
        selected_type=type_filter,
    )


@app.route("/transactions/add", methods=["GET", "POST"])
@login_required
def add_transaction():
    categories = Category.query.order_by(Category.name).all()

    if request.method == "POST":
        t_type = request.form.get("type")
        amount = request.form.get("amount", type=float)
        description = request.form.get("description", "").strip()
        category_id = request.form.get("category_id", type=int)
        date_str = request.form.get("date")

        error = None
        if t_type not in ("income", "expense"):
            error = "Please select a valid transaction type."
        elif amount is None or amount <= 0:
            error = "Amount must be a positive number."

        try:
            t_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
        except ValueError:
            error = "Invalid date format."
            t_date = date.today()

        if error:
            flash(error, "danger")
            return render_template("add_transaction.html", categories=categories)

        transaction = Transaction(
            user_id=current_user().id,
            category_id=category_id,
            type=t_type,
            amount=amount,
            description=description,
            date=t_date,
        )
        db.session.add(transaction)
        db.session.commit()
        flash("Transaction added.", "success")
        return redirect(url_for("transactions_list"))

    return render_template("add_transaction.html", categories=categories, today=date.today().isoformat())


@app.route("/transactions/<int:transaction_id>/edit", methods=["GET", "POST"])
@login_required
def edit_transaction(transaction_id):
    transaction = Transaction.query.filter_by(
        id=transaction_id, user_id=current_user().id
    ).first_or_404()
    categories = Category.query.order_by(Category.name).all()

    if request.method == "POST":
        t_type = request.form.get("type")
        amount = request.form.get("amount", type=float)
        description = request.form.get("description", "").strip()
        category_id = request.form.get("category_id", type=int)
        date_str = request.form.get("date")

        error = None
        if t_type not in ("income", "expense"):
            error = "Please select a valid transaction type."
        elif amount is None or amount <= 0:
            error = "Amount must be a positive number."

        try:
            t_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else transaction.date
        except ValueError:
            error = "Invalid date format."
            t_date = transaction.date

        if error:
            flash(error, "danger")
            return render_template("edit_transaction.html", transaction=transaction, categories=categories)

        transaction.type = t_type
        transaction.amount = amount
        transaction.description = description
        transaction.category_id = category_id
        transaction.date = t_date
        db.session.commit()

        flash("Transaction updated.", "success")
        return redirect(url_for("transactions_list"))

    return render_template("edit_transaction.html", transaction=transaction, categories=categories)


@app.route("/transactions/<int:transaction_id>/delete", methods=["POST"])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.filter_by(
        id=transaction_id, user_id=current_user().id
    ).first_or_404()
    db.session.delete(transaction)
    db.session.commit()
    flash("Transaction deleted.", "info")
    return redirect(url_for("transactions_list"))


# ---------------------------------------------------------------------------
# Budgeting
# ---------------------------------------------------------------------------

@app.route("/budget", methods=["GET", "POST"])
@login_required
def budget():
    user = current_user()
    categories = Category.query.order_by(Category.name).all()
    selected_month = request.args.get("month") or date.today().strftime("%Y-%m")

    if request.method == "POST":
        category_id = request.form.get("category_id", type=int)
        amount = request.form.get("amount", type=float)
        month = request.form.get("month") or selected_month

        if not category_id or amount is None or amount < 0:
            flash("Please provide a valid category and amount.", "danger")
        else:
            existing = Budget.query.filter_by(
                user_id=user.id, category_id=category_id, month=month
            ).first()
            if existing:
                existing.amount = amount
            else:
                db.session.add(
                    Budget(user_id=user.id, category_id=category_id, month=month, amount=amount)
                )
            db.session.commit()
            flash("Budget saved.", "success")
        return redirect(url_for("budget", month=month))

    budgets = Budget.query.filter_by(user_id=user.id, month=selected_month).all()

    # Compute actual spend per category for the selected month
    spend_by_category = defaultdict(float)
    month_transactions = [
        t for t in Transaction.query.filter_by(user_id=user.id, type="expense").all()
        if t.date.strftime("%Y-%m") == selected_month
    ]
    for t in month_transactions:
        cat_name = t.category.name if t.category else "Uncategorized"
        spend_by_category[cat_name] += t.amount

    budget_rows = []
    for b in budgets:
        spent = spend_by_category.get(b.category.name, 0.0)
        budget_rows.append({
            "category": b.category.name,
            "budgeted": b.amount,
            "spent": spent,
            "remaining": b.amount - spent,
            "over": spent > b.amount,
        })

    return render_template(
        "budget.html",
        categories=categories,
        budget_rows=budget_rows,
        selected_month=selected_month,
    )


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

@app.route("/reports")
@login_required
def reports():
    user = current_user()
    month = request.args.get("month") or date.today().strftime("%Y-%m")

    all_transactions = Transaction.query.filter_by(user_id=user.id).all()
    month_transactions = [t for t in all_transactions if t.date.strftime("%Y-%m") == month]

    total_income = sum(t.amount for t in month_transactions if t.type == "income")
    total_expense = sum(t.amount for t in month_transactions if t.type == "expense")
    net = total_income - total_expense

    category_breakdown = defaultdict(float)
    for t in month_transactions:
        if t.type == "expense":
            cat_name = t.category.name if t.category else "Uncategorized"
            category_breakdown[cat_name] += t.amount

    # Distinct months available, for the month picker
    available_months = sorted({t.date.strftime("%Y-%m") for t in all_transactions}, reverse=True)
    if month not in available_months:
        available_months = [month] + available_months

    return render_template(
        "reports.html",
        month=month,
        total_income=total_income,
        total_expense=total_expense,
        net=net,
        category_breakdown=dict(category_breakdown),
        available_months=available_months,
        transactions=sorted(month_transactions, key=lambda t: t.date),
    )


# ---------------------------------------------------------------------------
# JSON endpoint for lightweight chart data (used by dashboard/report charts)
# ---------------------------------------------------------------------------

@app.route("/api/category-summary")
@login_required
def api_category_summary():
    user = current_user()
    totals = defaultdict(float)
    for t in Transaction.query.filter_by(user_id=user.id, type="expense").all():
        cat_name = t.category.name if t.category else "Uncategorized"
        totals[cat_name] += t.amount
    return jsonify(totals)


# ---------------------------------------------------------------------------
# CLI / bootstrap
# ---------------------------------------------------------------------------

@app.cli.command("init-db")
def init_db():
    """Create tables and seed default categories."""
    db.create_all()
    seed_categories()
    print("Database initialized.")


def bootstrap():
    with app.app_context():
        db.create_all()
        seed_categories()


if __name__ == "__main__":
    bootstrap()
    app.run(debug=True)
