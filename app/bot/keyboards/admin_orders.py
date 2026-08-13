"""Admin orders keyboard with pagination."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.database.models.order import Order


class AdminOrdersKeyboard:
    """Admin orders inline keyboard builder."""

    PAGE_SIZE = 5  # تعداد سفارش‌ها در هر صفحه

    @staticmethod
    def get_recent_orders_keyboard(
        orders: list[Order], page: int = 1, total: int = 0
    ) -> InlineKeyboardMarkup:
        """Get paginated orders keyboard."""
        keyboard = []

        start_idx = (page - 1) * AdminOrdersKeyboard.PAGE_SIZE
        end_idx = start_idx + AdminOrdersKeyboard.PAGE_SIZE
        page_orders = orders[start_idx:end_idx]

        status_emoji = {
            "PENDING_PAYMENT": "⏳",
            "RECEIPT_SUBMITTED": "📤",
            "APPROVED": "✅",
            "REJECTED": "❌",
            "COMPLETED": "🎁",
            "CANCELLED": "🚫",
        }

        for order in page_orders:
            emoji = status_emoji.get(order.status.value, "❓")
            keyboard.append(
                [
                    InlineKeyboardButton(
                        text=f"{emoji} سفارش #{order.id} — {order.status.value}",
                        callback_data=f"admin_view_order:{order.id}",
                    )
                ]
            )

        if not page_orders:
            keyboard.append(
                [InlineKeyboardButton(text="📭 سفارشی وجود ندارد", callback_data="noop")]
            )

        # Pagination row
        total_pages = max(1, (total + AdminOrdersKeyboard.PAGE_SIZE - 1) // AdminOrdersKeyboard.PAGE_SIZE)
        nav_row = []

        if page > 1:
            nav_row.append(
                InlineKeyboardButton(text="◀️ قبلی", callback_data=f"admin_orders:page:{page - 1}")
            )
        else:
            nav_row.append(InlineKeyboardButton(text="•", callback_data="noop"))

        nav_row.append(
            InlineKeyboardButton(text=f"صفحه {page}/{total_pages}", callback_data="noop")
        )

        if page < total_pages:
            nav_row.append(
                InlineKeyboardButton(text="بعدی ▶️", callback_data=f"admin_orders:page:{page + 1}")
            )
        else:
            nav_row.append(InlineKeyboardButton(text="•", callback_data="noop"))

        keyboard.append(nav_row)

        # Filter row
        keyboard.append(
            [
                InlineKeyboardButton(text="⏳ در انتظار", callback_data="admin_orders:filter:RECEIPT_SUBMITTED:1"),
                InlineKeyboardButton(text="🎁 موفق", callback_data="admin_orders:filter:COMPLETED:1"),
                InlineKeyboardButton(text="❌ رد شده", callback_data="admin_orders:filter:REJECTED:1"),
            ]
        )

        keyboard.append(
            [InlineKeyboardButton(text="🔙 بازگشت به پنل", callback_data="admin_panel")]
        )

        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_order_review_keyboard(order_id: int) -> InlineKeyboardMarkup:
        """Get order review keyboard."""
        keyboard = [
            [
                InlineKeyboardButton(text="✅ تأیید پرداخت", callback_data=f"approve_order:{order_id}"),
                InlineKeyboardButton(text="❌ رد پرداخت", callback_data=f"reject_order:{order_id}"),
            ],
            [InlineKeyboardButton(text="🔙 بازگشت به لیست", callback_data="admin_orders:page:1")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_order_back_keyboard() -> InlineKeyboardMarkup:
        """Get back button for order details."""
        keyboard = [
            [InlineKeyboardButton(text="🔙 لیست سفارش‌ها", callback_data="admin_orders:page:1")],
            [InlineKeyboardButton(text="🔙 پنل اصلی", callback_data="admin_panel")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)