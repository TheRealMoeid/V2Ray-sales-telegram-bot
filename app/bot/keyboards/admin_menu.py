"""Admin menu keyboard."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


class AdminMenuKeyboard:
    """Admin panel inline keyboard builder."""

    @staticmethod
    def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
        """Get admin menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton(text="📊 آمار", callback_data="admin_statistics"),
            ],
            [
                InlineKeyboardButton(text="📦 مدیریت کانفیگ‌ها", callback_data="admin_configs"),
                InlineKeyboardButton(text="🛒 سفارش‌ها", callback_data="admin_orders"),
            ],
            [
                InlineKeyboardButton(text="👥 کاربران", callback_data="admin_users"),
            ],
            [
                InlineKeyboardButton(text="🔙 بازگشت به منو اصلی", callback_data="back_to_menu"),
            ],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
