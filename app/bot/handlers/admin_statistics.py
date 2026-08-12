"""Admin statistics handlers."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.filters.admin import AdminFilter
from app.services.statistics_service import StatisticsService

logger = logging.getLogger(__name__)
router = Router(name="admin_statistics")


@router.callback_query(F.data == "admin_statistics", AdminFilter())
async def handle_admin_statistics(callback: CallbackQuery, session: AsyncSession):
    """Handle admin statistics view."""
    try:
        # Get statistics
        stats = await StatisticsService.get_statistics(session)
        
        stats_text = f"""
📊 آمار فروشگاه

👥 تعداد کاربران: {stats['total_users']}
🛒 تعداد سفارش‌ها: {stats['total_orders']}
💰 مجموع فروش: {stats['total_sales']:,} تومان

✅ سفارش‌های موفق: {stats['completed_orders']}
⏳ سفارش‌های در انتظار: {stats['pending_orders']}
❌ سفارش‌های رد شده: {stats['rejected_orders']}

📦 کانفیگ‌های موجود: {stats['available_configs']}
📦 کانفیگ‌های فروخته شده: {stats['sold_configs']}

━━━━━━━━━━━━━━━━━━━━

📈 فروش امروز: {stats['today_sales']:,} تومان
📈 فروش این هفته: {stats['week_sales']:,} تومان
📈 فروش این ماه: {stats['month_sales']:,} تومان
"""
        
        await callback.message.edit_text(
            text=stats_text,
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in handle_admin_statistics: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)


@router.callback_query(F.data == "admin_users", AdminFilter())
async def handle_admin_users(callback: CallbackQuery, session: AsyncSession):
    """Handle admin users view."""
    try:
        # Get user count and recent users
        user_stats = await StatisticsService.get_user_statistics(session)
        
        users_text = f"""
👥 آمار کاربران

تعداد کل کاربران: {user_stats['total_users']}

کاربران جدید (۱۰ نفر آخر):
"""
        
        for user in user_stats['recent_users']:
            username = f"@{user.username}" if user.username else user.first_name
            users_text += f"\n• {username} (ID: {user.telegram_id})"
        
        await callback.message.edit_text(text=users_text)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in handle_admin_users: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)
