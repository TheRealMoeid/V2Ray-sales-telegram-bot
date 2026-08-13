"""Admin action audit log model."""

from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, func, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base


class AdminAction(Base):
    """Admin action audit log model."""

    __tablename__ = "admin_actions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    admin_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "order", "config"
    target_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    action_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    admin: Mapped["User"] = relationship("User", back_populates="admin_actions")

    def __repr__(self) -> str:
        return f"<AdminAction(id={self.id}, admin_id={self.admin_id}, action={self.action})>"
