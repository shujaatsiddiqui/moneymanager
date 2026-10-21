from datetime import date as date_type, datetime, timezone
from typing import Optional

from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Integer, String,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base

# Single user for now. Every table carries user_id so multi-user is a later,
# painless step instead of a rewrite.
USER_ID = 1

# Money is stored as integer cents to avoid floating point drift.


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, default=USER_ID, index=True)
    name: Mapped[str] = mapped_column(String(80))
    group_name: Mapped[str] = mapped_column(String(20))  # Cash / Accounts / Card / Savings
    is_liability: Mapped[bool] = mapped_column(Boolean, default=False)
    # Signed: for a card, a negative opening balance means you owe that amount.
    opening_cents: Mapped[int] = mapped_column(Integer, default=0)
    include_in_totals: Mapped[bool] = mapped_column(Boolean, default=True)
    is_business: Mapped[bool] = mapped_column(Boolean, default=False)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    # Last 4 digits of account number for auto-detection during import
    account_suffix: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    __table_args__ = (UniqueConstraint("user_id", "name"),)


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, default=USER_ID, index=True)
    name: Mapped[str] = mapped_column(String(80))
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    emoji: Mapped[str] = mapped_column(String(8), default="")
    exclude_from_budget: Mapped[bool] = mapped_column(Boolean, default=False)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    # Same subcategory name is allowed under different parents (e.g. "Car").
    __table_args__ = (UniqueConstraint("user_id", "parent_id", "name"),)


class Budget(Base):
    __tablename__ = "budgets"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, default=USER_ID, index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    month: Mapped[str] = mapped_column(String(7))  # YYYY-MM
    limit_cents: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (UniqueConstraint("user_id", "category_id", "month"),)


class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, default=USER_ID, index=True)
    date: Mapped[date_type] = mapped_column(Date, index=True)
    kind: Mapped[str] = mapped_column(String(15))  # expense / income / transfer_out / transfer_in
    amount_cents: Mapped[int] = mapped_column(Integer)  # always positive
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    to_account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    merchant: Mapped[str] = mapped_column(String(200), default="")
    note: Mapped[str] = mapped_column(String(500), default="")
    is_business: Mapped[bool] = mapped_column(Boolean, default=False)
    # Reserved for bank imports later (duplicate detection).
    import_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    __table_args__ = (UniqueConstraint("user_id", "import_hash"),)


class Rule(Base):
    __tablename__ = "rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, default=USER_ID, index=True)
    pattern: Mapped[str] = mapped_column(String(200))  # substring, or "re:<regex>"
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    priority: Mapped[int] = mapped_column(Integer, default=100)  # lower runs first
    min_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id"), nullable=True)
