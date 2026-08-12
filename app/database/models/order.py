"""Order model."""

from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Integer, String, DateTime, func, ForeignKey, Enum, Numeric
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

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
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
    admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(
        "User", 
        back_populates="orders",
        foreign_keys=[user_id]
    )
    product: Mapped["Product"] = relationship("Product", back_populates="orders")
    admin: Mapped["User | None"] = relationship(
        "User", 
        foreign_keys=[admin_id], 
        back_populates="admin_orders"
    )
    config: Mapped["Config | None"] = relationship(
        "Config", 
        back_populates="order",
        foreign_keys="[Config.order_id]"
    )
    receipt: Mapped["PaymentReceipt | None"] = relationship(
        "PaymentReceipt", 
        back_populates="order", 
        uselist=False,
        foreign_keys="[PaymentReceipt.order_id]"
    )

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, user_id={self.user_id}, status={self.status})>"
