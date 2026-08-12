"""Admin authorization filter."""
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from app.config.settings import settings


class AdminFilter(BaseFilter):
    """Filter to check if user is an admin."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        """Check if user is admin."""
        user_id = None
        
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        
        if user_id is None:
            return False
        
        return user_id in settings.admin_ids


# Alias for backward compatibility
IsAdminFilter = AdminFilter
