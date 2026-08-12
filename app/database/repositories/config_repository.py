"""Config repository."""

from typing import Optional
from datetime import datetime
from sqlalchemy import select, update, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.config import Config, ConfigStatus


class ConfigRepository:
    """Repository for Config model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, config_id: int) -> Optional[Config]:
        """Get config by ID."""
        result = await self.session.execute(
            select(Config).where(Config.id == config_id)
        )
        return result.scalar_one_or_none()

    async def get_available_for_product(self, product_id: int) -> list[Config]:
        """Get available configs for a specific product."""
        result = await self.session.execute(
            select(Config)
            .where(and_(Config.product_id == product_id, Config.status == ConfigStatus.AVAILABLE))
            .order_by(Config.created_at)
        )
        return list(result.scalars().all())

    async def get_available_count_for_product(self, product_id: int) -> int:
        """Count available configs for a specific product."""
        result = await self.session.execute(
            select(func.count())
            .select_from(Config)
            .where(and_(Config.product_id == product_id, Config.status == ConfigStatus.AVAILABLE))
        )
        return result.scalar() or 0

    async def get_all_available(self) -> list[Config]:
        """Get all available configs."""
        result = await self.session.execute(
            select(Config)
            .where(Config.status == ConfigStatus.AVAILABLE)
            .order_by(Config.created_at)
        )
        return list(result.scalars().all())

    async def create(self, product_id: int, config_text: str) -> Config:
        """Create a new config."""
        config = Config(product_id=product_id, config_text=config_text, status=ConfigStatus.AVAILABLE)
        self.session.add(config)
        await self.session.flush()
        return config

    async def assign_to_order(
        self, config_id: int, user_id: int, order_id: int
    ) -> Optional[Config]:
        """Assign a config to a user/order atomically."""
        # Use FOR UPDATE to lock the row
        stmt = (
            select(Config)
            .where(and_(Config.id == config_id, Config.status == ConfigStatus.AVAILABLE))
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            return None

        config.status = ConfigStatus.ASSIGNED
        config.assigned_to_user_id = user_id
        config.order_id = order_id
        config.assigned_at = datetime.utcnow()

        await self.session.flush()
        return config

    async def delete(self, config_id: int) -> bool:
        """Delete a config (only if AVAILABLE)."""
        config = await self.get_by_id(config_id)
        if not config or config.status != ConfigStatus.AVAILABLE:
            return False

        await self.session.delete(config)
        await self.session.flush()
        return True

    async def count_available(self) -> int:
        """Count total available configs."""
        result = await self.session.execute(
            select(func.count())
            .select_from(Config)
            .where(Config.status == ConfigStatus.AVAILABLE)
        )
        return result.scalar() or 0

    async def count_assigned(self) -> int:
        """Count total assigned configs."""
        result = await self.session.execute(
            select(func.count())
            .select_from(Config)
            .where(Config.status == ConfigStatus.ASSIGNED)
        )
        return result.scalar() or 0

    async def get_first_available_for_product(
        self, product_id: int, with_lock: bool = True
    ) -> Optional[Config]:
        """Get first available config for a product (for atomic assignment)."""
        stmt = (
            select(Config)
            .where(and_(Config.product_id == product_id, Config.status == ConfigStatus.AVAILABLE))
            .order_by(Config.created_at)
            .limit(1)
        )
        if with_lock:
            stmt = stmt.with_for_update()

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
