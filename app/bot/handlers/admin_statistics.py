"""Admin statistics handlers."""
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.admin import AdminFilter
from app.database.models.user import User
from app.services.statistics_service import StatisticsService

logger = logging.getLogger(__name__)
router = Router(name="admin_statistics")


@router.callback_query(F.data == "admin_statistics", AdminFilter())
async def handle_admin_statistics(callback: CallbackQuery, session: AsyncSession):
    """Handle admin statistics view."""
    try:
        # Instantiate service and call instance method (Bug #10 fix)
        stats_service = StatisticsService(session)
        stats = await stats_service.get_full_statistics()

        stats_text = f"""
📊 آمار فروشگاه

👥 تعداد کاربران: {stats.get('total_users', 0)}
🛒 تعداد سفارش‌ها: {stats.get('total_orders', 0)}
💰 مجموع فروش: {stats.get('total_sales', 0):,} تومان

✅ سفارش‌های موفق: {stats.get('completed_orders', 0)}
⏳ سفارش‌های در انتظار: {stats.get('pending_orders', 0)}
❌ سفارش‌های رد شده: {stats.get('rejected_orders', 0)}

📦 کانفیگ‌های موجود: {stats.get('available_configs', 0)}
📦 کانفیگ‌های فروخته شده: {stats.get('assigned_configs', 0)}

━━━━━━━━━━━━━━━━━━━━

📈 فروش امروز: {stats.get('today_sales', 0):,} تومان
📈 فروش این هفته: {stats.get('week_sales', 0):,} تومان
📈 فروش این ماه: {stats.get('month_sales', 0):,} تومان
"""

        await callback.message.edit_text(text=stats_text)
        await callback.answer()

    except Exception as e:
        logger.exception(f"Error in handle_admin_statistics: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)


@router.callback_query(F.data == "admin_users", AdminFilter())
async def handle_admin_users(callback: CallbackQuery, session: AsyncSession):
    """Handle admin users view."""
    try:
        # Query user stats directly since StatisticsService doesn't have get_user_statistics (Bug #10 fix)
        total_users_result = await session.execute(
            select(func.count()).select_from(User)
        )
        total_users = total_users_result.scalar() or 0

        recent_result = await session.execute(
            select(User).order_by(User.created_at.desc()).limit(10)
        )
        recent_users = recent_result.scalars().all()

        users_text = f"""
👥 آمار کاربران

تعداد کل کاربران: {total_users}

کاربران جدید (۱۰ نفر آخر):
"""

        for user in recent_users:
            username = f"@{user.username}" if user.username else user.first_name
            users_text += f"\n• {username} (ID: {user.telegram_id})"

        if not recent_users:
            users_text += "\nهنوز کاربری ثبت‌نام نکرده است."

        await callback.message.edit_text(text=users_text)
        await callback.answer()

    except Exception as e:
        logger.exception(f"Error in handle_admin_users: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)