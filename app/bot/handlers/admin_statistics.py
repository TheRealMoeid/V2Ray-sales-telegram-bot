"""Admin statistics handlers."""
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.admin import AdminFilter
from app.database.models.user import User
from app.services.statistics_service import StatisticsService

logger = logging.getLogger(__name__)
router = Router(name="admin_statistics")


def _back_to_admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت به پنل", callback_data="admin_panel")]
        ]
    )


@router.callback_query(F.data == "admin_statistics", AdminFilter())
async def handle_admin_statistics(callback: CallbackQuery, session: AsyncSession):
    """Handle admin statistics view."""
    try:
        stats_service = StatisticsService(session)
        stats = await stats_service.get_full_statistics()

        stats_text = f"""
📊 آمار فروشگاه

👥 کاربران: {stats.get('total_users', 0)}
🛒 سفارش‌ها: {stats.get('total_orders', 0)}
💰 مجموع فروش: {stats.get('total_sales', 0):,.0f} تومان

✅ موفق: {stats.get('completed_orders', 0)}
⏳ در انتظار: {stats.get('pending_orders', 0)} + 📤 ارسال شده: {stats.get('submitted_orders', 0) if 'submitted_orders' in stats else 0}
❌ رد شده: {stats.get('rejected_orders', 0)}

📦 موجود: {stats.get('available_configs', 0)} | فروخته: {stats.get('assigned_configs', 0)}

━━━━━━━━━━━━━━━━━━━━
📈 امروز: {stats.get('today_sales', 0):,.0f} تومان
📈 هفته: {stats.get('week_sales', 0):,.0f} تومان
📈 ماه: {stats.get('month_sales', 0):,.0f} تومان
"""

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="👥 ۱۰ کاربر اخیر", callback_data="admin_users:recent"),
                    InlineKeyboardButton(text="🛒 آخرین سفارش‌ها", callback_data="admin_orders:page:1"),
                ],
                [
                    InlineKeyboardButton(text="🔙 بازگشت به پنل", callback_data="admin_panel"),
                ],
            ]
        )

        await callback.message.edit_text(text=stats_text, reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        logger.exception(f"Error in handle_admin_statistics: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)


@router.callback_query(F.data == "admin_users", AdminFilter())
@router.callback_query(F.data == "admin_users:recent", AdminFilter())
async def handle_admin_users(callback: CallbackQuery, session: AsyncSession):
    """Handle admin users view."""
    try:
        total_result = await session.execute(select(func.count()).select_from(User))
        total_users = total_result.scalar() or 0

        recent_result = await session.execute(
            select(User).order_by(User.created_at.desc()).limit(10)
        )
        recent_users = recent_result.scalars().all()

        users_text = f"👥 **آمار کاربران**\n\nتعداد کل: {total_users}\n\n"
        users_text += "**۱۰ کاربر اخیر:**\n"

        if recent_users:
            for user in recent_users:
                name = f"@{user.username}" if user.username else (user.first_name or "بدون نام")
                users_text += f"• {name} (ID: `{user.telegram_id}`)\n"
        else:
            users_text += "_هنوز کاربری ثبت‌نام نکرده._"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 بازگشت به پنل", callback_data="admin_panel")]
            ]
        )

        await callback.message.edit_text(text=users_text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer()

    except Exception as e:
        logger.exception(f"Error in handle_admin_users: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)