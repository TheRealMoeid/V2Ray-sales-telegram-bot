"""Admin action repository."""

from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.admin_action import AdminAction


class AdminActionRepository:
    """Repository for AdminAction model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        admin_id: int,
        action: str,
        target_type: str,
        target_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AdminAction:
        """Create a new admin action log."""
        admin_action = AdminAction(
            admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata=metadata,
        )
        self.session.add(admin_action)
        await self.session.flush()
        return admin_action

    async def log_order_approval(
        self, admin_id: int, order_id: int, config_id: Optional[int] = None
    ) -> AdminAction:
        """Log order approval action."""
        return await self.create(
            admin_id=admin_id,
            action="approved_order",
            target_type="order",
            target_id=order_id,
            metadata={"config_id": config_id} if config_id else None,
        )

    async def log_order_rejection(
        self, admin_id: int, order_id: int, reason: str
    ) -> AdminAction:
        """Log order rejection action."""
        return await self.create(
            admin_id=admin_id,
            action="rejected_order",
            target_type="order",
            target_id=order_id,
            metadata={"reason": reason},
        )

    async def log_config_add(
        self, admin_id: int, config_id: int, product_id: int
    ) -> AdminAction:
        """Log config addition action."""
        return await self.create(
            admin_id=admin_id,
            action="added_config",
            target_type="config",
            target_id=config_id,
            metadata={"product_id": product_id},
        )

    async def log_config_delete(
        self, admin_id: int, config_id: int, product_id: Optional[int] = None
    ) -> AdminAction:
        """Log config deletion action."""
        return await self.create(
            admin_id=admin_id,
            action="deleted_config",
            target_type="config",
            target_id=config_id,
            metadata={"product_id": product_id} if product_id else None,
        )

    async def get_admin_actions(self, admin_id: int, limit: int = 50) -> list[AdminAction]:
        """Get recent actions by an admin."""
        result = await self.session.execute(
            select(AdminAction)
            .where(AdminAction.admin_id == admin_id)
            .order_by(AdminAction.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
