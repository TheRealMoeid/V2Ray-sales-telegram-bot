"""Admin menu keyboard."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class AdminMenuKeyboard:
    """Admin panel inline keyboard builder."""

    @staticmethod
    def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
        """Get admin menu keyboard (2x2 grid + back)."""
        keyboard = [
            [
                InlineKeyboardButton(text="📊 آمار", callback_data="admin_statistics"),
                InlineKeyboardButton(text="👥 کاربران", callback_data="admin_users"),
            ],
            [
                InlineKeyboardButton(text="📦 کانفیگ‌ها", callback_data="admin_configs"),
                InlineKeyboardButton(text="🛒 سفارش‌ها", callback_data="admin_orders:page:1"),
            ],
            [
                InlineKeyboardButton(text="🔙 بازگشت به منو مشتری", callback_data="back_to_menu"),
            ],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)