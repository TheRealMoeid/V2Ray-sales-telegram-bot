"""User orders keyboard."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.database.models.order import Order


class UserOrdersKeyboard:
    """User orders inline keyboard builder."""

    @staticmethod
    def get_orders_keyboard(orders: list[Order]) -> InlineKeyboardMarkup:
        """Get orders list keyboard."""
        keyboard = []
        
        for order in orders[:10]:  # Limit to 10 orders
            keyboard.append([
                InlineKeyboardButton(
                    text=f"سفارش #{order.id}",
                    callback_data=f"view_order:{order.id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_menu")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_order_back_keyboard() -> InlineKeyboardMarkup:
        """Get back button for order details."""
        keyboard = [
            [InlineKeyboardButton(text="🔙 بازگشت به لیست", callback_data="my_orders")],
            [InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="back_to_menu")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
