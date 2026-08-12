"""Payment info keyboard."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


class PaymentInfoKeyboard:
    """Payment info inline keyboard builder."""

    @staticmethod
    def get_payment_info_keyboard() -> InlineKeyboardMarkup:
        """Get payment info inline keyboard with back button."""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت", 
                    callback_data="back_to_menu"
                ),
            ],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
