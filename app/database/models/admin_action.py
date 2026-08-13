"""Admin action audit log model."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class AdminAction(Base):
    """Admin action audit log model."""

    __tablename__ = "admin_actions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    admin_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )  # Telegram ID, no FK (Bug #3 fix)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "order", "config"
    target_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    action_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Note: no `admin` relationship here. User.admin_actions (viewonly with
    # primaryjoin on telegram_id) covers reads; query User explicitly when needed.

    def __repr__(self) -> str:
        return f"<AdminAction(id={self.id}, admin_id={self.admin_id}, action={self.action})>"