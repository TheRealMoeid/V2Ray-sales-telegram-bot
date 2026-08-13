"""User model."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class User(Base):
    """Telegram user model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True
    )
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # View-only relationships joined on Telegram ID (no FK constraints - Bug #3 fix)
    orders: Mapped[list["Order"]] = relationship(
        "Order",
        primaryjoin="User.telegram_id == foreign(Order.user_id)",
        lazy="select",
        viewonly=True,
    )
    admin_orders: Mapped[list["Order"]] = relationship(
        "Order",
        primaryjoin="User.telegram_id == foreign(Order.admin_id)",
        lazy="select",
        viewonly=True,
    )
    configs: Mapped[list["Config"]] = relationship(
        "Config",
        primaryjoin="User.telegram_id == foreign(Config.assigned_to_user_id)",
        lazy="select",
        viewonly=True,
    )
    admin_actions: Mapped[list["AdminAction"]] = relationship(
        "AdminAction",
        primaryjoin="User.telegram_id == foreign(AdminAction.admin_id)",
        lazy="select",
        viewonly=True,
    )

    @property
    def is_admin(self) -> bool:
        """Admin status is determined by ADMIN_IDS env var, not the DB."""
        return False

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"