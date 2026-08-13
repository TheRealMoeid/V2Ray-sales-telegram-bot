"""Order model."""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class OrderStatus(str, PyEnum):
    """Order status enum."""

    PENDING_PAYMENT = "PENDING_PAYMENT"
    RECEIPT_SUBMITTED = "RECEIPT_SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Order(Base):
    """Order model for tracking purchases."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )  # Telegram ID, no FK
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="تومان")
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.PENDING_PAYMENT, index=True
    )
    receipt_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    receipt_file_unique_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    admin_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True
    )  # Telegram ID, no FK
    rejection_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    # Note: No direct relationship to User because user_id stores Telegram ID, not users.id
    # When user info is needed, query User table with telegram_id=user_id
    product: Mapped["Product"] = relationship("Product", back_populates="orders")
    config: Mapped["Config | None"] = relationship(
        "Config",
        back_populates="order",
        foreign_keys="[Config.order_id]",
    )
    receipt: Mapped["PaymentReceipt | None"] = relationship(
        "PaymentReceipt",
        back_populates="order",
        uselist=False,
        foreign_keys="[PaymentReceipt.order_id]",
    )

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, user_id={self.user_id}, status={self.status})>"