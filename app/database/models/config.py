"""Config model for V2Ray configurations."""

from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Integer, String, DateTime, func, ForeignKey, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base


class ConfigStatus(str, PyEnum):
    """Configuration status enum."""

    AVAILABLE = "AVAILABLE"
    ASSIGNED = "ASSIGNED"


class Config(Base):
    """V2Ray configuration model."""

    __tablename__ = "configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    config_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ConfigStatus] = mapped_column(
        Enum(ConfigStatus), default=ConfigStatus.AVAILABLE, index=True
    )
    assigned_to_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
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
    assigned_user: Mapped["User | None"] = relationship(
        "User", 
        back_populates="configs", 
        foreign_keys=[assigned_to_user_id]
    )
    order: Mapped["Order | None"] = relationship(
        "Order", 
        back_populates="config",
        foreign_keys=[order_id]
    )

    def __repr__(self) -> str:
        return f"<Config(id={self.id}, status={self.status}, product_id={self.product_id})>"
