"""Config model for V2Ray configurations."""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class ConfigStatus(str, PyEnum):
    """Configuration status enum."""

    AVAILABLE = "AVAILABLE"
    ASSIGNED = "ASSIGNED"


class Config(Base):
    """V2Ray configuration model."""

    __tablename__ = "configs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    config_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ConfigStatus] = mapped_column(
        Enum(ConfigStatus), default=ConfigStatus.AVAILABLE, index=True
    )
    assigned_to_user_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, index=True
    )  # Telegram ID, no FK (Bug #3 fix)
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="configs")
    order: Mapped["Order | None"] = relationship(
        "Order",
        back_populates="config",
        foreign_keys=[order_id],
    )
    # Note: no `assigned_user` relationship here. User.configs (viewonly with
    # primaryjoin on telegram_id) covers reads; query User explicitly when needed.

    def __repr__(self) -> str:
        return f"<Config(id={self.id}, status={self.status}, product_id={self.product_id})>"