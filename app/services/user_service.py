"""User service."""

from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repositories.user_repository import UserRepository
from app.database.models.user import User


class UserService:
    """Service for user-related business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def get_or_create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> Tuple[User, bool]:
        """
        Get existing user or create new one.
        Returns (user, created) tuple.
        """
        return await self.user_repo.get_or_create(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        return await self.user_repo.get_by_telegram_id(telegram_id)

    async def is_admin(self, telegram_id: int) -> bool:
        """Check if user is an admin."""
        from app.config.settings import settings

        return telegram_id in settings.ADMIN_IDS

    async def get_all_users(self) -> list[User]:
        """Get all users."""
        return await self.user_repo.get_all()

    async def count_users(self) -> int:
        """Count total users."""
        return await self.user_repo.count()
