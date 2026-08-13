"""User model."""

from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base


class User(Base):
    """Telegram user model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    orders: Mapped[list["Order"]] = relationship(
        "Order", 
        back_populates="user", 
        foreign_keys="[Order.user_id]",
        lazy="select"
    )
    configs: Mapped[list["Config"]] = relationship(
        "Config", 
        back_populates="assigned_user", 
        foreign_keys="[Config.assigned_to_user_id]", 
        lazy="select"
    )
    admin_orders: Mapped[list["Order"]] = relationship(
        "Order", 
        back_populates="admin", 
        foreign_keys="[Order.admin_id]", 
        lazy="select"
    )
    admin_actions: Mapped[list["AdminAction"]] = relationship(
        "AdminAction", 
        back_populates="admin", 
        lazy="select"
    )

    @property
    def is_admin(self) -> bool:
        """Check if user is admin (always False for regular users)."""
        return False

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"
