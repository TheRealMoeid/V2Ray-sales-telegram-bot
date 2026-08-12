"""Database session middleware."""
from typing import Callable, Any
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, InlineQuery
from app.database.session import async_session


class DatabaseSessionMiddleware(BaseMiddleware):
    """Middleware to provide database session to handlers."""

    async def __call__(
        self,
        handler: Callable,
        event: Message | CallbackQuery | InlineQuery,
        data: dict[str, Any],
    ) -> Any:
        """Add database session to handler data."""
        async with async_session() as session:
            data["session"] = session
            return await handler(event, data)
