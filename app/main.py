"""Main bot application."""
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.config.settings import settings
from app.database.session import async_session, init_db
from app.bot.middlewares.database import DatabaseSessionMiddleware
from app.bot.handlers.user_commands import router as user_commands_router
from app.bot.handlers.purchase import router as purchase_router
from app.bot.handlers.receipt import router as receipt_router
from app.bot.handlers.user_orders import router as user_orders_router
from app.bot.handlers.admin_commands import router as admin_commands_router
from app.bot.handlers.admin_orders import router as admin_orders_router
from app.bot.handlers.admin_config import router as admin_config_router
from app.bot.handlers.admin_statistics import router as admin_statistics_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """Execute on bot startup."""
    logger.info("Bot is starting up...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Log bot info
    me = await bot.get_me()
    logger.info(f"Bot started: @{me.username} (ID: {me.id})")
    logger.info(f"Admin IDs: {settings.admin_ids}")


async def on_shutdown(bot: Bot):
    """Execute on bot shutdown."""
    logger.info("Bot is shutting down...")
    await bot.session.close()


def register_routers(dp: Dispatcher):
    """Register all routers."""
    dp.include_router(user_commands_router)
    dp.include_router(purchase_router)
    dp.include_router(receipt_router)
    dp.include_router(user_orders_router)
    dp.include_router(admin_commands_router)
    dp.include_router(admin_orders_router)
    dp.include_router(admin_config_router)
    dp.include_router(admin_statistics_router)
    logger.info("All routers registered")


def register_middlewares(dp: Dispatcher):
    """Register all middlewares."""
    # Database session middleware for all handlers
    dp.message.middleware(DatabaseSessionMiddleware())
    dp.callback_query.middleware(DatabaseSessionMiddleware())
    logger.info("Middlewares registered")


async def main():
    """Main function to run the bot."""
    # Validate settings
    if not settings.bot_token:
        logger.error("BOT_TOKEN is not set in environment variables!")
        sys.exit(1)
    
    if not settings.database_url:
        logger.error("DATABASE_URL is not set in environment variables!")
        sys.exit(1)
    
    if not settings.admin_ids:
        logger.warning("ADMIN_IDS is not set! No one will have admin access.")
    
    # Create bot and dispatcher
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    
    # Register routers and middlewares
    register_routers(dp)
    register_middlewares(dp)
    
    # Register startup/shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Start polling
    logger.info("Starting bot polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
