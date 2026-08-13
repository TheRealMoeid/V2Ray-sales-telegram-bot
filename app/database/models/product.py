"""Product model."""

from datetime import datetime
from typing import TYPE_CHECKING

<<<<<<< HEAD
from sqlalchemy import BigInteger, String, DateTime, func, Boolean, Numeric, Integer
=======
from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Numeric, String, func
>>>>>>> 1f3dccd (fix: apply full code review fixes (bugs 1-23))
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

if TYPE_CHECKING:
    from app.database.models.config import Config
    from app.database.models.order import Order


class Product(Base):
    """Product model for V2Ray configurations."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="تومان")
    duration: Mapped[int] = mapped_column(Integer, default=30)  # in days
    protocol: Mapped[str] = mapped_column(String(50), default="VLESS")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    configs: Mapped[list["Config"]] = relationship(
        "Config", back_populates="product", lazy="select"
    )
    orders: Mapped[list["Order"]] = relationship(
        "Order", back_populates="product", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name={self.name}, price={self.price})>"