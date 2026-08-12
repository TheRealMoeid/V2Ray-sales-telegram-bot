"""Config service."""

from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repositories.config_repository import ConfigRepository
from app.database.models.config import Config, ConfigStatus


class ConfigService:
    """Service for config-related business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.config_repo = ConfigRepository(session)

    async def get_config_by_id(self, config_id: int) -> Optional[Config]:
        """Get config by ID."""
        return await self.config_repo.get_by_id(config_id)

    async def get_available_configs_for_product(
        self, product_id: int
    ) -> List[Config]:
        """Get available configs for a specific product."""
        return await self.config_repo.get_available_for_product(product_id)

    async def get_available_count_for_product(self, product_id: int) -> int:
        """Count available configs for a product."""
        return await self.config_repo.get_available_count_for_product(product_id)

    async def has_available_config(self, product_id: int) -> bool:
        """Check if product has available configs."""
        count = await self.get_available_count_for_product(product_id)
        return count > 0

    async def create_config(self, product_id: int, config_text: str) -> Config:
        """Create a new config."""
        return await self.config_repo.create(
            product_id=product_id, config_text=config_text
        )

    async def delete_config(self, config_id: int) -> bool:
        """Delete a config (only if AVAILABLE)."""
        return await self.config_repo.delete(config_id)

    async def get_all_available_configs(self) -> List[Config]:
        """Get all available configs."""
        return await self.config_repo.get_all_available()

    async def count_available(self) -> int:
        """Count total available configs."""
        return await self.config_repo.count_available()

    async def count_assigned(self) -> int:
        """Count total assigned configs."""
        return await self.config_repo.count_assigned()

    async def assign_config_to_order(
        self, config_id: int, user_id: int, order_id: int
    ) -> Tuple[Optional[Config], str]:
        """
        Assign a config to an order atomically.
        Returns (config, error_message).
        Error message is empty if successful.
        """
        config = await self.config_repo.assign_to_order(
            config_id=config_id, user_id=user_id, order_id=order_id
        )

        if not config:
            return None, "Config not available or already assigned"

        return config, ""

    async def get_first_available_for_product(
        self, product_id: int
    ) -> Optional[Config]:
        """Get first available config for a product (for atomic assignment)."""
        return await self.config_repo.get_first_available_for_product(product_id)
