"""Admin orders keyboard."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.database.models.order import Order


class AdminOrdersKeyboard:
    """Admin orders inline keyboard builder."""

    @staticmethod
    def get_recent_orders_keyboard(orders: list[Order]) -> InlineKeyboardMarkup:
        """Get recent orders keyboard."""
        keyboard = []
        
        for order in orders[:15]:  # Limit to 15 orders
            keyboard.append([
                InlineKeyboardButton(
                    text=f"سفارش #{order.id} - {order.status.value}",
                    callback_data=f"admin_view_order:{order.id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(text="🔙 بازگشت به پنل", callback_data="admin_panel")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_order_review_keyboard(order_id: int) -> InlineKeyboardMarkup:
        """Get order review keyboard with approve/reject buttons."""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="✅ تأیید پرداخت",
                    callback_data=f"approve_order:{order_id}"
                ),
                InlineKeyboardButton(
                    text="❌ رد پرداخت",
                    callback_data=f"reject_order:{order_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="admin_orders"
                ),
            ],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_order_back_keyboard() -> InlineKeyboardMarkup:
        """Get back button for order details."""
        keyboard = [
            [InlineKeyboardButton(text="🔙 بازگشت به لیست سفارش‌ها", callback_data="admin_orders")],
            [InlineKeyboardButton(text="🔙 بازگشت به پنل", callback_data="admin_panel")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
