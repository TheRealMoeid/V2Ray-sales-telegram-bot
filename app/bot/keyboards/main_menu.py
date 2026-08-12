"""Main menu keyboard."""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


class MainKeyboard:
    """Main menu keyboard builder."""

    @staticmethod
    def get_menu() -> ReplyKeyboardMarkup:
        """Get main menu keyboard."""
        keyboard = [
            [KeyboardButton(text="📦 خرید کانفیگ")],
            [KeyboardButton(text="📋 سفارش‌های من")],
            [KeyboardButton(text="ℹ️ راهنما"), KeyboardButton(text="💬 پشتیبانی")],
        ]
        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True,
            one_time_keyboard=False,
        )

    @staticmethod
    def get_back() -> ReplyKeyboardMarkup:
        """Get back button keyboard."""
        keyboard = [[KeyboardButton(text="🔙 بازگشت")]]
        return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
