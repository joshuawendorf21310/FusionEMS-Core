from enum import Enum
from typing import Optional
from datetime import datetime

from sqlalchemy import String, ForeignKey, Integer, Float, Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class Product(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Core product entity (e.g., "EMS Platform", "State Debt Setoff Module").
    """
    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    stripe_product_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=True)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)


class Module(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Distinct functional module that can be enabled/disabled.
    Linked to products for pricing, but tracked separately for entitlement.
    """
    __tablename__ = "modules"

    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)  # e.g., "STATE_DEBT_SETOFF"
    description: Mapped[str] = mapped_column(Text, nullable=True)
    product_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("products.id"), nullable=True)


class Price(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Versioned pricing record.
    Captures base price, per-call price, setup fee.
    """
    __tablename__ = "prices"

    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    module_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("modules.id"), nullable=True)
    
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)  # Base recurring
    currency: Mapped[str] = mapped_column(String(3), default="usd", nullable=False)
    interval: Mapped[str] = mapped_column(String(16), default="month", nullable=False)  # month, year
    
    # Metered usage components
    per_unit_amount_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # e.g. per call
    usage_type: Mapped[str] = mapped_column(String(16), default="licensed", nullable=False) # licensed, metered
    
    stripe_price_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=True)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)


class SubscriptionPlan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Internal representation of a tenant's subscription.
    Links to Stripe but controls Entitlements.
    """
    __tablename__ = "subscription_plans"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True)
    current_period_start: Mapped[datetime] = mapped_column(nullable=True)
    current_period_end: Mapped[datetime] = mapped_column(nullable=True)
    
    cancel_at_period_end: Mapped[bool] = mapped_column(default=False, nullable=False)


class SubscriptionItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Line items on a subscription (Base Platform, Extra User, Module X).
    """
    __tablename__ = "subscription_items"

    plan_id: Mapped[UUID] = mapped_column(ForeignKey("subscription_plans.id"), nullable=False)
    price_id: Mapped[UUID] = mapped_column(ForeignKey("prices.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(default=1, nullable=False)
    
    stripe_subscription_item_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)


class ContractOverride(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Founder-controlled overrides for specific agencies (Grandfathering).
    """
    __tablename__ = "contract_overrides"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    price_id: Mapped[UUID] = mapped_column(ForeignKey("prices.id"), nullable=False)
    
    override_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=True)
    valid_until: Mapped[Optional[datetime]] = mapped_column(nullable=True)


class PriceChangeAudit(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Audit trail for price changes.
    """
    __tablename__ = "price_change_audits"

    price_id: Mapped[UUID] = mapped_column(ForeignKey("prices.id"), nullable=False)
    changed_by_user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    old_value_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    new_value_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=True)
