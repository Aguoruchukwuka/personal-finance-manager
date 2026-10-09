from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

DEFAULT_CATEGORIES = ["Food", "Transport", "Utilities", "Savings", "Other"]


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship(
        "Transaction", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    budgets = db.relationship(
        "Budget", backref="user", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    transactions = db.relationship("Transaction", backref="category", lazy=True)
    budgets = db.relationship("Budget", backref="category", lazy=True)


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    type = db.Column(db.String(10), nullable=False)  # "income" or "expense"
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<Transaction {self.type} {self.amount}>"


class Budget(db.Model):
    __tablename__ = "budgets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    month = db.Column(db.String(7), nullable=False)  # format: "YYYY-MM"
    amount = db.Column(db.Float, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "category_id", "month", name="uq_budget_scope"),
    )


def seed_categories():
    """Ensure the default set of categories exists."""
    for name in DEFAULT_CATEGORIES:
        if not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name))
    db.session.commit()
